import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited geometry, sparse helpers, and PR #126 event-gap primitives.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

SMAG2=b'ESTAv001'; SH2='<8sBBBB4I4Q'; SH2S=struct.calcsize(SH2)

def encode_state(Q,order,valmode,level):
    zc=zstd.ZstdCompressor(level=level);P=np.transpose(Q,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=[];gaps=[];states=[]
    for row in tr:
        ch=np.empty(row.size,bool);ch[0]=row[0]!=0;ch[1:]=row[1:]!=row[:-1];pos=np.flatnonzero(ch);counts.append(pos.size)
        if pos.size:
            g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
            if pos.size>1:g[1:]=np.diff(pos)
            gaps.extend(g.tolist());states.extend(row[pos].astype(np.int32).tolist())
    counts=np.asarray(counts,np.uint16);gaps=np.asarray(gaps,np.int32);states=np.asarray(states,np.int32)
    cb=zc.compress(counts.astype('<u2',copy=False).tobytes());gb=zc.compress(leb128_u(gaps));v1=v2=b'';dc=1
    if valmode==0:
        dc=dtype_code(states);v1=zc.compress(states.astype(DT[dc],copy=False).tobytes())
    else:
        # 2-bit state alphabet: 0 -> 0, 1 -> +1, 2 -> -1, 3 -> exact exception.
        codes=np.zeros(states.size,np.uint8);codes[states==1]=1;codes[states==-1]=2;exc=(states!=0)&(states!=1)&(states!=-1);codes[exc]=3
        v1=zc.compress(pack2(codes));ex=states[exc];dc=dtype_code(ex);v2=zc.compress(ex.astype(DT[dc],copy=False).tobytes()) if ex.size else zc.compress(b'')
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(SH2,SMAG2,1,oc,valmode,dc,*Q.shape,len(cb),len(gb),len(v1),len(v2))
    parts={'counts':len(cb),'gaps':len(gb),'state1':len(v1),'state2':len(v2),'events':int(states.size),'zero_states':int(np.sum(states==0)),'plus1_states':int(np.sum(states==1)),'minus1_states':int(np.sum(states==-1)),'exception_states':int(np.sum((states!=0)&(states!=1)&(states!=-1))),'raw_varint_bytes':len(leb128_u(gaps))}
    return h+cb+gb+v1+v2,parts

def decode_state(blob):
    q=struct.unpack(SH2,blob[:SH2S]);magic,ver,oc,valmode,dc,d0,d1,d2,d3,lc,lg,l1,l2=q
    if magic!=SMAG2 or ver!=1:raise RuntimeError('state header')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(d0,d1,d2,d3);pshape=tuple(shape[i] for i in order)+(d3,);ntr=int(np.prod(pshape[:-1]));T=d3;p=SH2S
    cb=blob[p:p+lc];p+=lc;gb=blob[p:p+lg];p+=lg;v1=blob[p:p+l1];p+=l1;v2=blob[p:p+l2];p+=l2
    if p!=len(blob):raise RuntimeError('state length')
    zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());gaps=leb128_decode(zd.decompress(gb),ne)
    if valmode==0:states=np.frombuffer(zd.decompress(v1),dtype=DT[dc],count=ne).astype(np.int32)
    else:
        codes=unpack2(zd.decompress(v1),ne);exc=codes==3;states=np.zeros(ne,np.int32);states[codes==1]=1;states[codes==2]=-1
        if exc.any():states[exc]=np.frombuffer(zd.decompress(v2),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)
    tr=np.zeros((ntr,T),np.int32);k=0
    for i,c in enumerate(counts.tolist()):
        if c:
            g=gaps[k:k+c];pos=np.cumsum(g)-1
            if pos[-1]>=T:raise RuntimeError('state position range')
            st=states[k:k+c]
            for j in range(c):
                a=int(pos[j]);b=int(pos[j+1]) if j+1<c else T;tr[i,a:b]=st[j]
            k+=c
    if k!=ne:raise RuntimeError('state event count')
    P=tr.reshape(pshape);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def current_best_main(K):
    rr=[]
    for order in itertools.permutations((0,1,2)):
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K,order,vm,level);R=decode(b)
                if not np.array_equal(R,K):raise RuntimeError('current main decode')
                rr.append((len(b),order,vm,level,b,parts))
    return min(rr,key=lambda x:x[0])

def current_best_out(O):
    rr=[]
    for td in (False,True):
        A=delta(O,1) if td else O;K4=A.reshape(1,1,A.shape[0],A.shape[1])
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K4,(0,1,2),vm,level);R=decode(b).reshape(O.shape);R=undelta(R,1) if td else R
                if not np.array_equal(R,O):raise RuntimeError('current out gap decode')
                rr.append((len(b),'gap',td,vm,level,b,parts))
        for level in (19,22):
            for perm in ((0,1,2,3),(3,1,2,0)):
                for rep in (0,1,2):
                    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);R=undelta(R,1) if td else R
                    if not np.array_equal(R,O):raise RuntimeError('current out generic decode')
                    rr.append((len(b),'generic',td,rep,level,b,{'perm':list(perm)}))
    return min(rr,key=lambda x:x[0])

def state_best(Q):
    rr=[]
    for order in itertools.permutations((0,1,2)):
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode_state(Q,order,vm,level);R=decode_state(b)
                if not np.array_equal(R,Q):raise RuntimeError('state main decode')
                rr.append((len(b),order,vm,level,b,parts))
    return min(rr,key=lambda x:x[0]),sorted(rr,key=lambda x:x[0])

def state_best_out(O):
    Q4=O.reshape(1,1,O.shape[0],O.shape[1]);rr=[]
    for vm in (0,1):
        for level in (19,22):
            b,parts=encode_state(Q4,(0,1,2),vm,level);R=decode_state(b).reshape(O.shape)
            if not np.array_equal(R,O):raise RuntimeError('state out decode')
            rr.append((len(b),vm,level,b,parts))
    return min(rr,key=lambda x:x[0])

def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    cm=current_best_main(K);co=current_best_out(O);sm,allstate=state_best(G);so=state_best_out(O)
    # Encoder is allowed to mix the new main representation with the already-audited cheapest outlier representation.
    if so[0]<co[0]:ob=so[3];outkind=1;outmeta={'kind':'state','bytes':so[0],'mode':'raw' if so[1]==0 else 'ternary','level':so[2],'parts':so[4]}
    else:ob=co[5];outkind=0;outmeta={'kind':co[1],'bytes':co[0],'tdiff':co[2],'mode':co[3],'level':co[4],'parts':co[6]}
    fmt='<8sdQQB';top=struct.pack(fmt,b'ESTTOP01',eps,len(sm[4]),len(ob),outkind)+sm[4]+ob;hs=struct.calcsize(fmt);_,ee,lm,lo,kind=struct.unpack(fmt,top[:hs]);RG=decode_state(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if kind==1:RO=decode_state(obb).reshape(O.shape)
    else:
        if co[1]=='gap':
            A=decode(obb).reshape(O.shape);RO=undelta(A,1) if co[2] else A
        else:
            A=decode_out_sparse(obb);RO=undelta(A,1) if co[2] else A
    Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    current_top=struct.calcsize('<8sdQQB')+cm[0]+co[0]
    candidates=[]
    for r in allstate[:12]:candidates.append({'bytes':r[0],'order':list(r[1]),'mode':'raw' if r[2]==0 else 'ternary','level':r[3],'parts':r[5]})
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'current_event_gap':{'main_bytes':cm[0],'outlier_bytes':co[0],'container_bytes_est':current_top,'ratio_est':raw/current_top,'main_order':list(cm[1]),'main_mode':'signed' if cm[2]==0 else 'signmag','main_level':cm[3],'main_parts':cm[5]},'event_state_best':{'main_bytes':sm[0],'order':list(sm[1]),'mode':'raw' if sm[2]==0 else 'ternary','level':sm[3],'parts':sm[5]},'event_state_candidates':candidates,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_sz3':szb/len(top)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_event_state.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
