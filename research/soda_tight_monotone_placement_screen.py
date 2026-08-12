import json,math,os,sys
import numpy as np

# Reuse PR #189's exact winning 5%-std state fields, refined context/Rice
# grammar, geometry, phase-map accounting, outlier dictionary and backend menu.
src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

class BitWriter:
    def __init__(self):self.buf=bytearray();self.acc=0;self.nbits=0;self.total=0
    def put(self,v,n):
        v=int(v);n=int(n)
        if n<0 or (n and (v<0 or v.bit_length()>n)):raise RuntimeError(('bit put',v,n))
        self.total+=n
        if n:
            self.acc|=v<<self.nbits;self.nbits+=n
            while self.nbits>=8:self.buf.append(self.acc&255);self.acc>>=8;self.nbits-=8
    def finish(self):
        if self.nbits:self.buf.append(self.acc&255);self.acc=0;self.nbits=0
        return bytes(self.buf),int(self.total)
class BitReader:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.acc=0;self.nbits=0;self.total=0
    def get(self,n):
        n=int(n)
        while self.nbits<n:
            if self.i>=len(self.b):raise RuntimeError(('bit underflow',n,self.total,len(self.b)))
            self.acc|=int(self.b[self.i])<<self.nbits;self.nbits+=8;self.i+=1
        if not n:return 0
        m=(1<<n)-1;v=self.acc&m;self.acc>>=n;self.nbits-=n;self.total+=n;return int(v)

def trace_starts(rc,startg,lens,T):
    rc=np.asarray(rc,np.int32);startg=np.asarray(startg,np.int32);lens=np.asarray(lens,np.int32);rows=[];k=0
    for n0 in rc.tolist():
        n=int(n0);prev=-1;ss=[]
        for j in range(n):
            g=int(startg[k]);ln=int(lens[k]);st=prev+g
            if st<0 or st+ln>T or (j and g<2):raise RuntimeError(('source placement',st,ln,g,T))
            ss.append(st);prev=st+ln-1;k+=1
        rows.append(np.asarray(ss,np.int32))
    if k!=len(lens):raise RuntimeError(('source accounting',k,len(lens)))
    return rows

def placement_params(starts,lens,T):
    n=len(starts)
    if not n:return np.empty(0,np.int32),int(T)
    y=np.empty(n,np.int32);off=0
    for i in range(n):y[i]=int(starts[i])-off;off+=int(lens[i])+1
    S=int(T)-int(np.sum(lens,dtype=np.int64))-(n-1)
    if S<0 or np.any(y<0) or np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('slack invariant',S,y[:8].tolist()))
    return y,S

def startg_from_y_rows(rc,lens,yrows,T):
    rc=np.asarray(rc,np.int32);lens=np.asarray(lens,np.int32);g=[];k=0
    if len(yrows)!=len(rc):raise RuntimeError('y row count')
    for i,n0 in enumerate(rc.tolist()):
        n=int(n0);ys=np.asarray(yrows[i],np.int32)
        if len(ys)!=n:raise RuntimeError(('y count',i,len(ys),n))
        if not n:continue
        S=int(T)-int(np.sum(lens[k:k+n],dtype=np.int64))-(n-1)
        if S<0 or np.any(ys<0) or np.any(ys>S) or np.any(np.diff(ys)<0):raise RuntimeError(('decoded slack',i,S))
        off=0;prev=-1
        for j in range(n):
            st=int(ys[j])+off;gg=st-prev
            if gg<1 or (j and gg<2):raise RuntimeError(('decoded gap',i,j,gg))
            g.append(gg);prev=st+int(lens[k+j])-1;off+=int(lens[k+j])+1
        if prev>=T:raise RuntimeError(('decoded beyond T',i,prev,T))
        k+=n
    if k!=len(lens):raise RuntimeError(('decoded placement accounting',k,len(lens)))
    return np.asarray(g,np.int32)

def ef_encode(rc,startg,lens,T):
    rows=trace_starts(rc,startg,lens,T);lw=BitWriter();hw=BitWriter();k=0;theory=0.0
    for n0,st in zip(np.asarray(rc).tolist(),rows):
        n=int(n0)
        if not n:continue
        ls=np.asarray(lens[k:k+n],np.int32);y,S=placement_params(st,ls,T);U=S+1;L=0
        if U>n:L=max(0,int(U//n).bit_length()-1)
        mask=(1<<L)-1 if L else 0
        for v in y.tolist():lw.put(int(v)&mask,L)
        H=(S>>L)+n;prev=-1
        for j,v in enumerate(y.tolist()):
            pos=(int(v)>>L)+j;gap=pos-prev-1
            if gap<0:raise RuntimeError('EF ordering')
            hw.put(0,gap);hw.put(1,1);prev=pos
        hw.put(0,H-prev-1);k+=n
    if k!=len(lens):raise RuntimeError('EF accounting')
    low,lb=lw.finish();high,hb=hw.finish();return low,high,{'low_bits':lb,'high_bits':hb,'total_bits':lb+hb,'raw_bytes':len(low)+len(high)}
def ef_decode(rc,lens,T,low,high):
    lr=BitReader(low);hr=BitReader(high);out=[];k=0;el=eh=0
    for i,n0 in enumerate(np.asarray(rc).tolist()):
        n=int(n0)
        if not n:out.append(np.empty(0,np.int32));continue
        ls=np.asarray(lens[k:k+n],np.int32);S=int(T)-int(np.sum(ls,dtype=np.int64))-(n-1);U=S+1;L=0
        if U>n:L=max(0,int(U//n).bit_length()-1)
        lows=[lr.get(L) for _ in range(n)];H=(S>>L)+n;highs=[]
        for pos in range(H):
            if hr.get(1):highs.append(pos-len(highs))
        if len(highs)!=n:raise RuntimeError(('EF ones',i,len(highs),n))
        y=np.asarray([(highs[j]<<L)|lows[j] for j in range(n)],np.int32)
        if np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('EF y',i,S))
        out.append(y);el+=n*L;eh+=H;k+=n
    if k!=len(lens) or lr.total!=el or hr.total!=eh:raise RuntimeError('EF decode accounting')
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
    if r!=0:raise RuntimeError(('combinadic residue',r,n,N))
    return np.asarray([z[i]-i for i in range(n)],np.int32)
def enum_encode(rc,startg,lens,T):
    rows=trace_starts(rc,startg,lens,T);w=BitWriter();k=0;theory=0.0
    for i,(n0,st) in enumerate(zip(np.asarray(rc).tolist(),rows)):
        n=int(n0)
        if not n:continue
        ls=np.asarray(lens[k:k+n],np.int32);y,S=placement_params(st,ls,T);N=S+n;tot=math.comb(N,n);width=(tot-1).bit_length();rank=colex_rank(y)
        if rank<0 or rank>=tot:raise RuntimeError(('rank range',i,rank,tot))
        w.put(rank,width);theory+=math.log2(tot) if tot>1 else 0.0;k+=n
    if k!=len(lens):raise RuntimeError('enum accounting')
    b,bits=w.finish();return b,b'',{'rank_bits':bits,'raw_bytes':len(b),'sum_log2_states':theory,'fixed_width_overhead_bits':bits-theory}
def enum_decode(rc,lens,T,b):
    r=BitReader(b);out=[];k=0;expected=0
    for i,n0 in enumerate(np.asarray(rc).tolist()):
        n=int(n0)
        if not n:out.append(np.empty(0,np.int32));continue
        ls=np.asarray(lens[k:k+n],np.int32);S=int(T)-int(np.sum(ls,dtype=np.int64))-(n-1);N=S+n;tot=math.comb(N,n);width=(tot-1).bit_length();rank=r.get(width)
        if rank>=tot:raise RuntimeError(('decoded rank',i,rank,tot))
        y=colex_unrank(rank,n,N)
        if np.any(y<0) or np.any(y>S) or np.any(np.diff(y)<0):raise RuntimeError(('enum y',i,S))
        out.append(y);expected+=width;k+=n
    if k!=len(lens) or r.total!=expected:raise RuntimeError('enum decode accounting')
    return out

def comp_pair(a,b):
    ba=compress_exact(a);bb=compress_exact(b)
    return {'bytes':int(ba[0]+bb[0]),'a_bytes':int(ba[0]),'b_bytes':int(bb[0]),'a_method':METHOD_NAMES[int(ba[1])],'b_method':METHOD_NAMES[int(bb[1])],'a_raw_bytes':len(a),'b_raw_bytes':len(b)}

def placement_screen(K,current_main_bytes,current_parts):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER);T=int(K.shape[-1]);current=int(current_parts['first_starts']+current_parts['inter_starts'])
    candidates=[]
    low,high,ed=ef_encode(rc,startg,lens,T);yr=ef_decode(rc,lens,T,low,high);rg=startg_from_y_rows(rc,lens,yr,T)
    if not np.array_equal(rg,startg):raise RuntimeError('EF exact placement decode')
    c=comp_pair(low,high);c.update({'name':'elias-fano','diag':ed});candidates.append(c)
    eb,empty,dd=enum_encode(rc,startg,lens,T);yr=enum_decode(rc,lens,T,eb);rg=startg_from_y_rows(rc,lens,yr,T)
    if not np.array_equal(rg,startg):raise RuntimeError('enumerative exact placement decode')
    c=comp_pair(eb,b'');c.update({'name':'enumerative-combinadic','diag':dd});candidates.append(c)
    candidates.sort(key=lambda x:x['bytes']);best=candidates[0];pred=int(current_main_bytes-current+best['bytes'])
    return {'current_placement_bytes':current,'current_first_bytes':int(current_parts['first_starts']),'current_inter_bytes':int(current_parts['inter_starts']),'best':best,'all':candidates,'predicted_main_bytes':pred,'predicted_main_saving_bytes':int(current_main_bytes-pred),'runs':int(len(lens)),'events':int(np.sum(lens))}

def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy)
    arms=[]
    # Exact PR #189 nearest arm.
    G,O=nearest_states(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);RK=decode_refined_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('nearest main audit')
    bo=best_out(O);container=TOP_HS+len(mb)+int(bo[0]);sc=placement_screen(K,len(mb),parts);sc['predicted_container_bytes']=int(container-sc['predicted_main_saving_bytes']);arms.append({'state':'nearest','current_container_bytes':container,'main_bytes':len(mb),'outlier_bytes':int(bo[0]),'screen':sc})
    # Exact PR #189 16-phase arm, including already-measured phase-map bytes.
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);RK=decode_refined_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('phase main audit')
    bo=best_out(O);top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);sc=placement_screen(K,len(mb),parts);sc['predicted_container_bytes']=int(len(top)-sc['predicted_main_saving_bytes']);arms.append({'state':'phase16','current_container_bytes':len(top),'main_bytes':len(mb),'outlier_bytes':int(bo[0]),'phase_bytes':int(pacct['main_phase_bytes']+pacct['out_phase_bytes']+PHHS),'screen':sc})
    szb,sze=sz3_bytes(X,public_eps);rows=[]
    for a in arms:
        p=int(a['screen']['predicted_container_bytes']);rows.append({'state':a['state'],'current_bytes':int(a['current_container_bytes']),'placement_name':a['screen']['best']['name'],'placement_bytes':int(a['screen']['best']['bytes']),'current_placement_bytes':int(a['screen']['current_placement_bytes']),'predicted_bytes':p,'predicted_saving_bytes':int(a['current_container_bytes']-p),'predicted_gain_vs_direct_sz3':float(szb/p),'clears_2x':bool(p<=szb/2),'screen':a['screen']})
    rows.sort(key=lambda r:r['predicted_bytes']);best=rows[0];out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'strict_two_x_target_bytes':szb/2,'best':best,'arms':rows}
    print(json.dumps({'target':out['strict_two_x_target_bytes'],'best_state':best['state'],'placement':best['placement_name'],'current_bytes':best['current_bytes'],'current_placement':best['current_placement_bytes'],'new_placement':best['placement_bytes'],'predicted_bytes':best['predicted_bytes'],'saving':best['predicted_saving_bytes'],'gain_sz3':best['predicted_gain_vs_direct_sz3'],'clears_2x':best['clears_2x']},indent=2),flush=True);json.dump(out,open('soda_tight_monotone_placement_screen.json','w'),indent=2)

main(sys.argv[1])
