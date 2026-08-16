import json,sys,struct
import h5py,numpy as np
from numba import njit
import imperial_near2eps_learned_zsm_fullhard as z
import imperial_near2eps_full_hard_128x30000 as f
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

C=128;NT=30000;P=32;TRAIN=1024;HEADER=48
CONFIGS=((128,2048),(64,2048),(32,2048),(16,2048),(8,2048),(1,2048),(32,1024),(16,1024),(8,1024),(1,1024),(16,512),(8,512),(1,512))
TOP_PHYSICAL=5


def fit_huber_q(Q):
    n=C*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);j=0
    for c in range(C):
        x=np.asarray(Q[c,:TRAIN],np.float64)
        for t in range(P,TRAIN):A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
    co=np.linalg.lstsq(A,y,rcond=None)[0]
    for _ in range(6):
        r=y-A@co;w=np.minimum(1.0,1.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
    return np.asarray(co,np.float32)


def ar_model_frame(co):
    raw=np.asarray(co,np.float32).astype('<f4').tobytes();zz=m.Z.compress(raw)
    use=len(zz)<len(raw);stored=zz if use else raw;rr=m.D.decompress(stored) if use else stored
    cd=np.frombuffer(rr,dtype='<f4').copy()
    if not np.array_equal(cd.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('AR model roundtrip')
    return len(stored)+24,('zstd' if use else 'raw'),cd

@njit(cache=True)
def ar_pred(Q,c,t,co,p):
    if t<p:return 0
    v=float(co[0])
    for j in range(p):v+=float(co[j+1])*float(Q[c,t-1-j])
    return int(np.rint(v))

@njit(cache=True)
def predictor_fields(Q,dts,dcs,lco,intercept,scale,aco,p):
    DL=np.empty(Q.shape,np.int32);DA=np.empty(Q.shape,np.int32)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):
            pl=g._pred(Q,c,t,dts,dcs,lco,intercept,scale);pa=ar_pred(Q,c,t,aco,p)
            DL[c,t]=int(Q[c,t])-pl;DA[c,t]=int(Q[c,t])-pa
    return DL,DA


def gamma_cost(A):
    x=np.abs(np.asarray(A,np.int64));out=np.ones(x.shape,np.float64);nz=x>0
    out[nz]=3.0+2.0*np.floor(np.log2(x[nz].astype(np.float64)))
    return out


def make_selector(DL,DA,gc,bt):
    lc=gamma_cost(DL);ac=gamma_cost(DA);ngc=(C+gc-1)//gc;ngt=(NT+bt-1)//bt;S=np.zeros((ngc,ngt),np.uint8)
    for ic in range(ngc):
        c0=ic*gc;c1=min(C,c0+gc)
        for it in range(ngt):
            t0=it*bt;t1=min(NT,t0+bt)
            if float(ac[c0:c1,t0:t1].sum()) < float(lc[c0:c1,t0:t1].sum()):S[ic,it]=1
    D=np.empty_like(DL)
    for ic in range(ngc):
        c0=ic*gc;c1=min(C,c0+gc)
        for it in range(ngt):
            t0=it*bt;t1=min(NT,t0+bt);D[c0:c1,t0:t1]=DA[c0:c1,t0:t1] if S[ic,it] else DL[c0:c1,t0:t1]
    return S,D,float(np.minimum.reduce([lc,ac]).sum()),float(np.mean(S))


def selector_frame(S,gc,bt):
    raw=np.packbits(np.asarray(S,np.uint8).ravel(),bitorder='little').tobytes();zz=m.Z.compress(raw);use=len(zz)<len(raw);stored=zz if use else raw
    hdr=struct.pack('<4sHHHHBI',b'SEL1',S.shape[0],S.shape[1],gc,bt,1 if use else 0,len(stored));buf=hdr+stored
    off=0;magic,nc,nt,gc2,bt2,use2,L=struct.unpack_from('<4sHHHHBI',buf,off);off+=17
    if magic!=b'SEL1' or gc2!=gc or bt2!=bt:raise RuntimeError('selector header')
    ss=buf[off:off+L];rr=m.D.decompress(ss) if use2 else ss;bits=np.unpackbits(np.frombuffer(rr,np.uint8),bitorder='little')[:nc*nt].astype(np.uint8).reshape(nc,nt)
    if not np.array_equal(bits,S):raise RuntimeError('selector replay')
    return len(buf),bits

@njit(cache=True)
def decode_hybrid(D,S,gc,bt,dts,dcs,lco,intercept,scale,aco,p):
    Q=np.empty(D.shape,np.int32)
    for t in range(D.shape[1]):
        it=t//bt
        for c in range(D.shape[0]):
            ic=c//gc
            if S[ic,it]:pr=ar_pred(Q,c,t,aco,p)
            else:pr=g._pred(Q,c,t,dts,dcs,lco,intercept,scale)
            Q[c,t]=pr+int(D[c,t])
    return Q


def zsm_materialize(D):
    screens=[]
    for W in z.WINDOWS:
        bb,nb=z.encode_zsm(D,W,z.SCREEN);screens.append((len(bb),W,int(nb)))
    _,W,_=min(screens);bb,nbit=z.encode_zsm(D,W,NT);Dd=z.decode_zsm(bb,nbit,W,D.shape)
    if not np.array_equal(Dd,D):raise RuntimeError(('ZSM D replay',W))
    return len(bb),int(W),int(nbit),Dd,{str(w):int(n) for n,w,_ in screens}


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,f.C0:f.C0+C],np.float64).T
    h,Q,DL0,dts,dcs,lco,intercept,changes,meanlegal=z.build_full(X,eps)
    lmb,lmrep,ddt,ddc,dlco,dinter=g.model_frame(dts,dcs,lco,intercept)
    aco=fit_huber_q(Q);amb,amrep,aco2=ar_model_frame(aco)
    DL,DA=predictor_fields(Q,ddt,ddc,dlco,dinter,g.SCALE,aco2,P)
    if not np.array_equal(DL,DL0):raise RuntimeError('learned field mismatch')
    cand=[]
    cand.append({'kind':'learned','D':DL,'sur':float(gamma_cost(DL).sum()),'selector_fraction':0.0})
    cand.append({'kind':'ar','D':DA,'sur':float(gamma_cost(DA).sum()),'selector_fraction':1.0})
    for gc,bt in CONFIGS:
        S,D,sur,frac=make_selector(DL,DA,gc,bt);sb,Sd=selector_frame(S,gc,bt);cand.append({'kind':f'hybrid_c{gc}_t{bt}','D':D,'S':Sd,'gc':gc,'bt':bt,'selector_bytes':sb,'sur':sur,'selector_fraction':frac})
    cand.sort(key=lambda q:q['sur']);physical=[];seen=set()
    picks=[]
    for q in cand:
        if q['kind'] in ('learned','ar') or len(picks)<TOP_PHYSICAL:
            if q['kind'] not in seen:picks.append(q);seen.add(q['kind'])
    for q in picks:
        pb,W,nbit,Dd,screens=zsm_materialize(q['D'])
        if q['kind']=='learned':
            total=lmb+pb+HEADER+1;Qd=f.q_decode(Dd,ddt,ddc,dlco,dinter,g.SCALE);models={'learned_model_bytes':int(lmb)};selb=0
        elif q['kind']=='ar':
            total=amb+pb+HEADER+1;S=np.ones((1,1),np.uint8);Qd=decode_hybrid(Dd,S,C,NT,ddt,ddc,dlco,dinter,g.SCALE,aco2,P);models={'ar_model_bytes':int(amb)};selb=0
        else:
            selb=int(q['selector_bytes']);total=lmb+amb+selb+pb+HEADER+1;Qd=decode_hybrid(Dd,q['S'],q['gc'],q['bt'],ddt,ddc,dlco,dinter,g.SCALE,aco2,P);models={'learned_model_bytes':int(lmb),'ar_model_bytes':int(amb)}
        if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',q['kind']))
        me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',q['kind'],me,eps))
        row={'kind':q['kind'],'bytes':int(total),'bps':8*total/X.size,'zsm_payload_bytes':int(pb),'zsm_window':W,'zsm_bits':nbit,'selector_bytes':selb,'selector_fraction':float(q.get('selector_fraction',0.0)),'surrogate':float(q['sur']),'zero_fraction':float(np.mean(q['D']==0)),'defect_std':float(q['D'].astype(np.float64).std()),'maxerr':me,'screens':screens,**models};physical.append(row);print(json.dumps(row,indent=2),flush=True)
    physical.sort(key=lambda r:r['bytes']);best=physical[0];champ=2478995;sz3=2767977
    out={'region':'hard','c0':f.C0,'shape':[C,NT],'global_std':std,'eps':eps,'hfac':z.FAC,'h':h,'mean_legal_states':meanlegal,'projection_changes':int(changes),'learned_model_rep':lmrep,'ar_model_rep':amrep,'candidate_surrogates':[{k:v for k,v in q.items() if k not in ('D','S')} for q in cand],'physical':physical,'best':best,'historical_huber_ar32_zsm_bytes':champ,'gain_vs_historical':champ/best['bytes'],'matched_sz3_bytes':sz3,'gain_vs_sz3':sz3/best['bytes'],'scope':'Decoder-real shared-computation predictor-routing gate on the identical near-2epsilon Q reconstruction. The decoder can compute both the charged learned sparse space-time predictor and a charged robust temporal AR32 predictor from already decoded Q. Public candidate selector granularities partition channel/time into fixed regions; each one-bit selector chooses the predictor with lower local gamma-length surrogate. Selector maps are physically packed/compressed, decoded and charged. Only a small surrogate-screened set plus both endpoint predictors are then encoded with the exact historical ZSM arithmetic backend. Decoder reads model(s)+selector+ZSM defects, causally regenerates exact Q and verifies unchanged source hard error. Final decision is by real bytes against the historical 2,478,995 B same-block champion.'}
    json.dump(out,open('imperial_near2eps_hybrid_predictor_zsm.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['kind'],'bytes':best['bytes'],'historical':champ,'gain_historical':champ/best['bytes'],'sz3':sz3,'gain_sz3':sz3/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
