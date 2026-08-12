import json,math,os,struct,sys
import numpy as np

# Reuse PR #167's exact lattice/run/value/backend machinery.  This experiment
# changes only the placement of already-defined contiguous runs.
src=open('research/soda_intergap_context_refine.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_context_refine.py','exec'),globals())

MMAG=b'MONPLC01'
MHDR='<8sBBBB4I10B10Q'
MHS=struct.calcsize(MHDR)

class BitWriter:
    def __init__(self): self.buf=bytearray();self.acc=0;self.nbits=0;self.total=0
    def put(self,v,n):
        n=int(n);v=int(v)
        if n<0 or (n and (v<0 or v.bit_length()>n)): raise RuntimeError(('bit put',v,n))
        self.total+=n
        if n:
            self.acc |= v << self.nbits; self.nbits += n
            while self.nbits>=8:
                self.buf.append(self.acc&255);self.acc >>= 8;self.nbits-=8
    def finish(self):
        if self.nbits:self.buf.append(self.acc&255);self.acc=0;self.nbits=0
        return bytes(self.buf),int(self.total)

class BitReader:
    def __init__(self,b): self.b=memoryview(b);self.i=0;self.acc=0;self.nbits=0;self.total=0
    def get(self,n):
        n=int(n)
        while self.nbits<n:
            if self.i>=len(self.b):raise RuntimeError(('bit underflow',n,self.total,len(self.b)))
            self.acc |= int(self.b[self.i]) << self.nbits;self.nbits+=8;self.i+=1
        if not n:return 0
        m=(1<<n)-1;v=self.acc&m;self.acc>>=n;self.nbits-=n;self.total+=n;return int(v)


def trace_starts(rc,startg,lens,T):
    rc=np.asarray(rc,np.int32);startg=np.asarray(startg,np.int32);lens=np.asarray(lens,np.int32);out=[];k=0
    for n0 in rc.tolist():
        n=int(n0);prev=-1;ss=[]
        for _ in range(n):
            g=int(startg[k]);ln=int(lens[k]);s=prev+g
            if s<0 or s+ln>T or (ss and s<=ss[-1]+int(lens[k-1])):raise RuntimeError(('bad source run placement',s,ln,prev,g,T))
            ss.append(s);prev=s+ln-1;k+=1
        out.append(np.asarray(ss,np.int32))
    if k!=len(lens):raise RuntimeError(('source run accounting',k,len(lens)))
    return out


def slack_coords(starts,lens):
    n=len(starts);S=None
    if not n:return np.empty(0,np.int32),0
    # T is supplied by caller when S is needed; this helper returns only offsets.
    y=np.empty(n,np.int32);off=0
    for i in range(n):y[i]=int(starts[i])-off;off+=int(lens[i])+1
    return y,off


def placement_params(starts,lens,T):
    n=len(starts)
    if not n:return np.empty(0,np.int32),int(T)
    y,_=slack_coords(starts,lens);S=int(T)-int(np.sum(lens,dtype=np.int64))-(n-1)
    if S<0 or np.any(y<0) or np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('slack invariant',S,y[:8].tolist(),lens[:8].tolist()))
    return y,S


def startg_from_y_rows(rc,lens,yrows,T):
    rc=np.asarray(rc,np.int32);lens=np.asarray(lens,np.int32);g=[];k=0
    if len(yrows)!=len(rc):raise RuntimeError('y row count')
    for i,n0 in enumerate(rc.tolist()):
        n=int(n0);ys=np.asarray(yrows[i],np.int32)
        if len(ys)!=n:raise RuntimeError(('y trace count',i,len(ys),n))
        if not n:continue
        S=int(T)-int(np.sum(lens[k:k+n],dtype=np.int64))-(n-1)
        if S<0 or np.any(ys<0) or np.any(ys>S) or np.any(np.diff(ys)<0):raise RuntimeError(('decoded slack invariant',i,S))
        off=0;prev=-1
        for j in range(n):
            s=int(ys[j])+off;gg=s-prev
            if gg<1 or (j and gg<2):raise RuntimeError(('decoded gap invariant',i,j,gg,s,prev))
            g.append(gg);prev=s+int(lens[k+j])-1;off+=int(lens[k+j])+1
        if prev>=T:raise RuntimeError(('decoded run beyond T',i,prev,T))
        k+=n
    if k!=len(lens):raise RuntimeError(('decoded placement accounting',k,len(lens)))
    return np.asarray(g,np.int32)


def ef_encode(rc,startg,lens,T):
    rows=trace_starts(rc,startg,lens,T);lw=BitWriter();hw=BitWriter();k=0;diag={'trace_bits':[]}
    for i,(n0,st) in enumerate(zip(np.asarray(rc).tolist(),rows)):
        n=int(n0)
        if not n:continue
        ls=np.asarray(lens[k:k+n],np.int32);y,S=placement_params(st,ls,T);U=S+1
        L=0
        if U>n:
            q=U//n;L=max(0,int(q).bit_length()-1)
        mask=(1<<L)-1 if L else 0
        for v in y.tolist():lw.put(int(v)&mask,L)
        H=(S>>L)+n;prev=-1
        for j,v in enumerate(y.tolist()):
            pos=(int(v)>>L)+j;gap=pos-prev-1
            if gap<0:raise RuntimeError(('EF order',i,j,pos,prev))
            hw.put(0,gap);hw.put(1,1);prev=pos
        hw.put(0,H-prev-1)
        diag['trace_bits'].append({'trace':i,'n':n,'S':S,'L':L,'low_bits':n*L,'high_bits':H})
        k+=n
    if k!=len(lens):raise RuntimeError('EF encode accounting')
    low,lb=lw.finish();high,hb=hw.finish();diag.update({'low_bits':lb,'high_bits':hb,'total_bits':lb+hb,'raw_bytes':len(low)+len(high)})
    return low,high,diag


def ef_decode(rc,lens,T,low,high):
    lr=BitReader(low);hr=BitReader(high);out=[];k=0;expected_low=expected_high=0
    for i,n0 in enumerate(np.asarray(rc).tolist()):
        n=int(n0)
        if not n:out.append(np.empty(0,np.int32));continue
        ls=np.asarray(lens[k:k+n],np.int32);S=int(T)-int(np.sum(ls,dtype=np.int64))-(n-1);U=S+1
        if S<0:raise RuntimeError(('EF S',i,S))
        L=0
        if U>n:
            q=U//n;L=max(0,int(q).bit_length()-1)
        lows=[lr.get(L) for _ in range(n)];H=(S>>L)+n;highs=[]
        for pos in range(H):
            if hr.get(1):highs.append(pos-len(highs))
        if len(highs)!=n:raise RuntimeError(('EF ones',i,len(highs),n,H))
        y=np.asarray([(highs[j]<<L)|lows[j] for j in range(n)],np.int32)
        if np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('EF y',i,S,y[:12].tolist()))
        out.append(y);expected_low+=n*L;expected_high+=H;k+=n
    if k!=len(lens) or lr.total!=expected_low or hr.total!=expected_high:raise RuntimeError(('EF decode accounting',k,len(lens),lr.total,expected_low,hr.total,expected_high))
    return out


def colex_rank(y):
    r=0
    for i,v in enumerate(np.asarray(y).tolist()):r+=math.comb(int(v)+i,i+1)
    return int(r)


def colex_unrank(r,n,N):
    r=int(r);n=int(n);N=int(N);z=[0]*n;upper=N-1
    for i in range(n,0,-1):
        lo=i-1;hi=upper;best=i-1
        while lo<=hi:
            m=(lo+hi)//2;c=math.comb(m,i)
            if c<=r:best=m;lo=m+1
            else:hi=m-1
        z[i-1]=best;r-=math.comb(best,i);upper=best-1
    if r!=0:raise RuntimeError(('combinadic residue',r,n,N,z[:8]))
    return np.asarray([z[i]-i for i in range(n)],np.int32)


def enum_encode(rc,startg,lens,T):
    rows=trace_starts(rc,startg,lens,T);w=BitWriter();k=0;theory=0;td=[]
    for i,(n0,st) in enumerate(zip(np.asarray(rc).tolist(),rows)):
        n=int(n0)
        if not n:continue
        ls=np.asarray(lens[k:k+n],np.int32);y,S=placement_params(st,ls,T);N=S+n;tot=math.comb(N,n);width=(tot-1).bit_length();rank=colex_rank(y)
        if rank<0 or rank>=tot:raise RuntimeError(('rank range',i,rank,tot,n,S))
        w.put(rank,width);theory+=math.log2(tot) if tot>1 else 0.0;td.append({'trace':i,'n':n,'S':S,'width':width,'log2_states':math.log2(tot) if tot>1 else 0.0});k+=n
    if k!=len(lens):raise RuntimeError('enum encode accounting')
    b,bits=w.finish();return b,b'',{'rank_bits':bits,'raw_bytes':len(b),'sum_log2_states':theory,'fixed_width_overhead_bits':bits-theory,'trace_bits':td}


def enum_decode(rc,lens,T,b):
    r=BitReader(b);out=[];k=0;expected=0
    for i,n0 in enumerate(np.asarray(rc).tolist()):
        n=int(n0)
        if not n:out.append(np.empty(0,np.int32));continue
        ls=np.asarray(lens[k:k+n],np.int32);S=int(T)-int(np.sum(ls,dtype=np.int64))-(n-1);N=S+n;tot=math.comb(N,n);width=(tot-1).bit_length();rank=r.get(width)
        if rank>=tot:raise RuntimeError(('decoded rank range',i,rank,tot,width))
        y=colex_unrank(rank,n,N)
        if np.any(y<0) or np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('enum y',i,S,y[:12].tolist()))
        out.append(y);expected+=width;k+=n
    if k!=len(lens) or r.total!=expected:raise RuntimeError(('enum decode accounting',k,len(lens),r.total,expected))
    return out


def prepare_new(K,order,mode):
    cache=prepare_common(K,order);sh,dc,raw,meta,rc,lens,rcomp,inter=cache
    sh2,rc2,startg,lens2,rcomp2,vals,phase,event_first,diag=gather_universal(K,order)
    if not np.array_equal(rc,rc2) or not np.array_equal(lens,lens2):raise RuntimeError('common/gather drift')
    T=int(K.shape[-1])
    if mode==1:a,b,pdiag=ef_encode(rc,startg,lens,T);name='elias-fano'
    elif mode==2:a,b,pdiag=enum_encode(rc,startg,lens,T);name='enumerative-combinadic'
    else:raise ValueError(mode)
    newraw=list(raw);newraw[1]=a;newraw[2]=b
    return sh,dc,newraw,{**meta,'placement_mode':mode,'placement_name':name,'placement_diag':pdiag},rc,lens


def encode_new(K,order,mode):
    sh,dc,raw,meta,rc,lens=prepare_new(K,order,mode);methods=[];frames=[];choices=[]
    for i,r in enumerate(raw):
        best,allrows=best_comp(r);n,m,b=best;methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(MHDR,MMAG,1,oc,dc,int(mode),*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','placement_a','placement_b','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=MHS;parts['backend_choices']=choices;parts.update(meta)
    return h+b''.join(frames),parts


def decode_new(blob):
    q=struct.unpack(MHDR,blob[:MHS]);magic,ver,oc,dc,mode,C,L,S,T,*rest=q
    if magic!=MMAG or ver!=1 or mode not in (1,2):raise RuntimeError(('monotone header',magic,ver,mode))
    methods=rest[:10];lf=rest[10:];p=MHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('monotone stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());nn=int(np.count_nonzero(rc))
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    yrows=ef_decode(rc,runlens,T,raw[1],raw[2]) if mode==1 else enum_decode(rc,runlens,T,raw[1]);startg=startg_from_y_rows(rc,runlens,yrows,T);rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        sg=bool(firstsign[fk]);fk+=1;signs[k]=sg;k+=1
        for _ in range(1,c):
            if not repeat[rk]:sg=not sg
            rk+=1;signs[k]=sg;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('monotone sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('monotone value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    cache=prepare_common(K,order);common=compress_common(cache[2]);bb,bparts=encode_kind(K,3,order,cache,common);BR=decode_kind(bb)
    if not np.array_equal(BR,K):raise RuntimeError('baseline exact K')
    rows=[{'mode':0,'name':'PR167-singleton-relative-rank','main_bytes':len(bb),'parts':bparts,'blob':bb}]
    for mode in (1,2):
        print('PLACEMENT MODE',mode,flush=True);b,parts=encode_new(K,order,mode);R=decode_new(b)
        if not np.array_equal(R,K):raise RuntimeError(('monotone exact K',mode))
        rows.append({'mode':mode,'name':parts['placement_name'],'main_bytes':len(b),'parts':parts,'blob':b});print(json.dumps({'mode':mode,'name':parts['placement_name'],'main_bytes':len(b),'placement_a':parts['placement_a'],'placement_b':parts['placement_b'],'timing_bytes':parts['timing_bytes'],'placement_diag':{k:v for k,v in parts['placement_diag'].items() if k!='trace_bits'}},indent=2),flush=True)
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];RK=decode_kind(best['blob']) if best['mode']==0 else decode_new(best['blob']);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('monotone outlier decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133226
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'prior_pr167_bytes':63657,'improvement_vs_pr167_bytes':int(63657-container)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','improvement_vs_pr167_bytes','maxerr','valid')},indent=2),flush=True);json.dump(out,open('soda_monotone_run_placement.json','w'),indent=2)

main(sys.argv[1])
