import itertools,json,math,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, PR #126 outlier codec, varints, sparse helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

CMAG=b'COFFv001'; CHDR='<8sBBBBB4I7Q'; CHS=struct.calcsize(CHDR)


def pack_fixed(a,bits):
    a=np.asarray(a,np.uint16).ravel();out=bytearray((a.size*bits+7)//8);acc=0;nb=0;j=0;mask=(1<<bits)-1
    for vv in a.tolist():
        v=int(vv)
        if v>mask:raise RuntimeError(('fixed-width overflow',v,bits))
        acc|=v<<nb;nb+=bits
        while nb>=8:out[j]=acc&255;j+=1;acc>>=8;nb-=8
    if nb:out[j]=acc&255
    return bytes(out)
def unpack_fixed(b,n,bits):
    out=np.empty(n,np.uint16);acc=0;nb=0;j=0;k=0;mask=(1<<bits)-1;bb=memoryview(b)
    while k<n:
        while nb<bits:acc|=int(bb[j])<<nb;j+=1;nb+=8
        out[k]=acc&mask;acc>>=bits;nb-=bits;k+=1
    return out


def sign_alt_planes(vals,counts):
    signs=vals<0;first=[];repeat=[];k=0;rep=0;trans=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=signs[k:k+c];first.append(int(s[0]))
        if c>1:
            r=(s[1:]==s[:-1]);repeat.extend(r.astype(np.uint8).tolist());rep+=int(r.sum());trans+=c-1
        k+=c
    if k!=vals.size:raise RuntimeError('sign count')
    return np.asarray(first,np.uint8),np.asarray(repeat,np.uint8),{'repeat_sign_fraction':rep/max(1,trans),'repeat_sign_count':rep,'sign_transitions':trans,'nonempty_traces':len(first)}


def gather(K,order,B):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);dq=[];offs=[];vals=[];same_block=0
    for row in tr:
        pos=np.flatnonzero(row).astype(np.int32);c=pos.size
        if not c:continue
        q=pos//B;r=pos%B;d=np.empty(c,np.int32);d[0]=q[0]+1
        if c>1:d[1:]=q[1:]-q[:-1]
        same_block+=int(np.count_nonzero(d[1:]==0)) if c>1 else 0;dq.extend(d.tolist());offs.extend(r.tolist());vals.extend(row[pos].astype(np.int32).tolist())
    return sh,counts,np.asarray(dq,np.int32),np.asarray(offs,np.uint16),np.asarray(vals,np.int32),{'same_block_events':same_block,'same_block_fraction':same_block/max(1,int(counts.sum())),'block_size':B}


def encode_main(K,order,B,omode,level):
    zc=zstd.ZstdCompressor(level=level);sh,counts,dq,offs,vals,diag=gather(K,order,B);bits=int(math.log2(B));cb=zc.compress(counts.astype('<u2',copy=False).tobytes());db=zc.compress(leb128_u(dq));oraw=offs.astype(np.uint8,copy=False).tobytes() if omode==0 else pack_fixed(offs,bits);ob=zc.compress(oraw);first,repeat,sdiag=sign_alt_planes(vals,counts);s1=zc.compress(np.packbits(first,bitorder='little').tobytes());s2=zc.compress(np.packbits(repeat,bitorder='little').tobytes());ab=np.abs(vals);exc=ab!=1;eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);mb=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'');oc=int(order[0]|(order[1]<<2)|(order[2]<<4));bc=bits;h=struct.pack(CHDR,CMAG,1,oc,bc,omode,dc,*K.shape,len(cb),len(db),len(ob),len(s1),len(s2),len(eb),len(mb));parts={'counts':len(cb),'block_delta':len(db),'offsets':len(ob),'offset_raw_bytes':len(oraw),'sign_first':len(s1),'sign_repeat':len(s2),'exception_support':len(eb),'exception_magnitude':len(mb),'timing_bytes':len(cb)+len(db)+len(ob),'value_bytes':len(s1)+len(s2)+len(eb)+len(mb),'block_delta_raw_bytes':len(leb128_u(dq)),'offset_mode':'uint8' if omode==0 else 'bitpacked','order':list(order),'level':level,**diag,**sdiag};return h+cb+db+ob+s1+s2+eb+mb,parts


def decode_main(blob):
    q=struct.unpack(CHDR,blob[:CHS]);magic,ver,oc,bits,omode,dc,C,L,S,T,lc,ld,lo,l1,l2,le,lm=q
    if magic!=CMAG or ver!=1:raise RuntimeError('coarse-offset header')
    B=1<<bits;p=CHS;cb=blob[p:p+lc];p+=lc;db=blob[p:p+ld];p+=ld;ob=blob[p:p+lo];p+=lo;s1=blob[p:p+l1];p+=l1;s2=blob[p:p+l2];p+=l2;eb=blob[p:p+le];p+=le;mb=blob[p:p+lm];p+=lm
    if p!=len(blob):raise RuntimeError('coarse-offset length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());dq=leb128_decode(zd.decompress(db),ne);orr=zd.decompress(ob);offs=np.frombuffer(orr,np.uint8,count=ne).astype(np.int32) if omode==0 else unpack_fixed(orr,ne,bits).astype(np.int32)
    nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(s1),np.uint8),bitorder='little',count=nn).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(s2),np.uint8),bitorder='little',count=ne-nn).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(mb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:continue
        d=dq[k:k+c];r=offs[k:k+c];qq=np.empty(c,np.int32);qq[0]=int(d[0])-1
        if c>1:qq[1:]=qq[0]+np.cumsum(d[1:],dtype=np.int32)
        pos=qq*B+r
        if pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0):raise RuntimeError(('coarse positions',i,B,pos[:6].tolist()))
        tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('coarse event count')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def best_out(O):
    rows=[]
    for td in (False,True):
        A=delta(O,1) if td else O;K4=A.reshape(1,1,A.shape[0],A.shape[1])
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K4,(0,1,2),vm,level);R=decode(b).reshape(O.shape);RR=undelta(R,1) if td else R
                if not np.array_equal(RR,O):raise RuntimeError('out gap')
                rows.append((len(b),'gap',td,vm,level,None,b,parts))
        for level in (19,22):
            for perm in ((0,1,2,3),(3,1,2,0)):
                for rep in (0,1,2):
                    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
                    if not np.array_equal(RR,O):raise RuntimeError('out generic')
                    rows.append((len(b),'generic',td,rep,level,perm,b,{}))
    return min(rows,key=lambda x:x[0])


def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for order in itertools.permutations((0,1,2)):
        for B in (4,8,16,32,64,128):
            for om in (0,1):
                for level in (19,22):
                    b,parts=encode_main(K,order,B,om,level);R=decode_main(b)
                    if not np.array_equal(R,K):raise RuntimeError(('coarse-offset K decode',order,B,om,level))
                    rows.append((len(b),order,B,om,level,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'COTOP001',eps,len(bm[5]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[5]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_main(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'order':list(r[1]),'block_size':r[2],'offset_mode':'uint8' if r[3]==0 else 'bitpacked','level':r[4],'parts':r[6]} for r in rows[:30]];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':69722}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_coarse_offset_timing.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
