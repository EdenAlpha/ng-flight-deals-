import json,math,struct,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133;TRAIN=4096
INC=2468803;STATE_WIN=2464965;MATCHED_SZ3=2767977
FORM=np.array([1,16,-1,1],np.int16) # constant, prevK, prev2K, leftK

def clip4(x):return int(max(-4,min(4,int(x))))+4
def wrap(x):return int(((int(x)+RAD)%STEP)-RAD)
def geom(K,c,t):
    prev=int(K[c,t-1]) if t else 0;prev2=int(K[c,t-2]) if t>1 else 0;left=int(K[c-1,t]) if c else 0
    bp=wrap(int(FORM[0])+int(FORM[1])*prev+int(FORM[2])*prev2+int(FORM[3])*left)
    ci=clip4(prev)*9+clip4(left)
    return ci,bp

def build(X,co,corr,nt,collect=False):
    Xi=np.rint(X[:,:nt]).astype(np.int64);R=np.zeros((C,nt),np.int32);K=np.zeros((C,nt),np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    if collect:cs=np.empty(C*nt,np.int32);nv=np.empty(C*nt,np.int64);bpv=np.empty(C*nt,np.int16);q=0
    for t in range(nt):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            ci,bp=geom(K,c,t);d=wrap(bp+int(corr[ci]));n=int(Xi[c,t])-p;k=(n-d+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',c,t,p,d,k,r))
            K[c,t]=k;R[c,t]=r
            if collect:cs[q]=ci;nv[q]=n;bpv[q]=bp;q+=1
    return (R,K,cs,nv,bpv) if collect else (R,K)
def phase_score(n,bp,q):
    d=((bp.astype(np.int64)+int(q)+RAD)%STEP)-RAD;k=np.floor_divide(n-d+RAD,STEP);return rc.proxy_cost_k(k)
def best_q(n,bp,seed):
    if len(n)>20000:
        z=np.linspace(0,len(n)-1,20000,dtype=np.int64);n=n[z];bp=bp[z]
    best=(1e300,int(seed))
    for q in list(range(-RAD,RAD+1,8))+[RAD]:
        s=phase_score(n,bp,q)
        if s<best[0]:best=(s,q)
    cen=best[1]
    for q in range(max(-RAD,cen-8),min(RAD,cen+8)+1):
        s=phase_score(n,bp,q)
        if s<best[0]:best=(s,q)
    return int(best[1])
def refit(cs,n,bp,old):
    order=np.argsort(cs,kind='stable');ss=cs[order];nn=n[order];bb=bp[order];u,ix,cnt=np.unique(ss,return_index=True,return_counts=True);tab=old.copy()
    for g,i,z in zip(u,ix,cnt):
        if z<64:continue
        tab[int(g)]=best_q(nn[i:i+z],bb[i:i+z],tab[int(g)])
    return tab
def train(X,co):
    corr=np.zeros(81,np.int16);hist=[]
    for it in range(3):
        R,K,cs,n,bp=build(X,co,corr,TRAIN,True);hist.append({'iter':it,'proxy_bps':rc.proxy_cost_k(K)/(C*TRAIN),'nonzero_corrections':int(np.count_nonzero(corr))});nc=refit(cs,n,bp,corr)
        if np.array_equal(nc,corr):break
        corr=nc
    R,K=build(X,co,corr,NT,False);return corr,R,K,hist
def side_frame(corr):
    raw=np.asarray(corr,dtype='<i2').tobytes();zc=zstd.ZstdCompressor(level=19).compress(raw);mode=1 if len(zc)<len(raw) else 0;store=zc if mode else raw
    return struct.pack('<4s4hBHI',b'FCL1',*[int(x) for x in FORM],mode,len(corr),len(store))+store
def parse_side(bb):
    magic,a,b,c,d,mode,n,L=struct.unpack_from('<4s4hBHI',bb,0)
    if magic!=b'FCL1' or len(bb)!=19+L:raise RuntimeError('side header')
    raw=zstd.ZstdDecompressor().decompress(bb[19:],max_output_size=2*n) if mode else bb[19:]
    corr=np.frombuffer(raw,dtype='<i2').copy()
    if len(corr)!=81 or [a,b,c,d]!=[int(x) for x in FORM]:raise RuntimeError('side content')
    return corr
def parse_k(stream,shape):
    off=0;entries={}
    for comp in cg.COMPONENTS:
        sid,nb,L=struct.unpack_from('<BQI',stream,off);off+=13;entries[comp]=(int(sid),int(nb),bytes(stream[off:off+L]));off+=L
    if off!=len(stream):raise RuntimeError('K trailing')
    return cg.decode_components(entries,shape)
def decode(K,co,corr):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for t in range(K.shape[1]):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            ci,bp=geom(K,c,t);R[c,t]=p+wrap(bp+int(corr[ci]))+STEP*int(K[c,t])
    return R
def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);corr,R,K,hist=train(X,cod);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('encode hard',me,eps))
    side=side_frame(corr);stream,_,chosen=rc.encode_fixed(K);corr2=parse_side(side);Kd=parse_k(stream,K.shape);cod2=np.frombuffer(model[:4*(ah.P+1)],np.float32).copy();Rd=decode(Kd,cod2,corr2)
    if not np.array_equal(Kd,K) or not np.array_equal(Rd,R):raise RuntimeError('physical replay')
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
    if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',mer,eps))
    out={'winner':'formula_plus_prev_left_correction','bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'prior_state_win_bytes':STATE_WIN,'delta_vs_prior_state_win':int(total-STATE_WIN),'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'eps':eps,'maxerr':mer,'formula_coefficients':[int(x) for x in FORM],'correction_contexts':81,'nonzero_corrections':int(np.count_nonzero(corr)),'side_bytes':len(side),'component_stream_bytes':len(stream),'model_bytes':len(model),'proxy_bps':rc.k_proxy(K),'train':hist,'chosen':chosen,'scope':'Exact composed GCA reconstruction law. The compact congruential phase program discovered in PR656 supplies a base phase from prevK/prev2K/leftK; a small 81-state correction table indexed by clipped prevK and leftK learns the residual phase geometry. Formula coefficients and the exact correction table are physically serialized (table raw or Zstd, whichever is smaller) and charged. The resulting full K stream is physically encoded and independently parsed; decoder regenerates the formula+correction phase at each sample, replays AR32 and verifies the unchanged hard-error bound.'};json.dump(out,open('imperial_gca_formula_correction_law.json','w'),indent=2);print(json.dumps({'summary':{k:v for k,v in out.items() if k not in ('train','chosen')}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
