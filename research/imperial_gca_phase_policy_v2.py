import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133;NEW_INC=2465652
# (channel-group size, previous-K clip radius, use diagonal sign, public time segments)
SPECS=[(16,4,0,1),(8,4,0,1),(4,4,0,1),(1,4,0,1),(8,8,0,1),(16,4,1,1),(16,4,0,4),(8,4,0,4),(16,4,0,8)]

def s3v(x):return np.where(x<0,0,np.where(x>0,2,1)).astype(np.int64)
def gamma_cost(k):
    a=np.abs(np.asarray(k,dtype=np.int64));z=np.ones(a.shape,np.float64);nz=a>0
    if np.any(nz):z[nz]+=2+2*np.floor(np.log2(a[nz]))
    return z

def nctx(spec):
    gs,pc,diag,tseg=spec;ng=(C+gs-1)//gs;return ng*(2*pc+1)*3*(3 if diag else 1)*tseg

def ctx_matrix(K,spec):
    gs,pc,diag,tseg=spec;ng=(C+gs-1)//gs;P=2*pc+1
    Tcat=np.minimum(tseg-1,(np.arange(NT,dtype=np.int64)*tseg)//NT)
    out=np.empty((C,NT),np.int32)
    for c in range(C):
        prev=np.empty(NT,np.int64);prev[0]=0;prev[1:]=K[c,:-1];prev=np.clip(prev,-pc,pc)+pc
        left=np.zeros(NT,np.int64) if c==0 else s3v(K[c-1])
        q=((c//gs)*P+prev)*3+left
        if diag:
            dg=np.ones(NT,np.int64)
            if c>0 and NT>1:dg[1:]=s3v(K[c-1,:-1])
            q=q*3+dg
        q=q*tseg+Tcat;out[c]=q.astype(np.int32)
    return out

def fit_table(N,K,spec):
    ctx=ctx_matrix(K,spec);nc=nctx(spec);tab=np.zeros(nc,np.int16);flatc=ctx.reshape(-1);flatn=N.reshape(-1);used=0
    for j in np.unique(flatc):
        idx=np.flatnonzero(flatc==j);used+=1
        cap=512 if nc>1000 else 1024
        if len(idx)>cap:idx=idx[np.linspace(0,len(idx)-1,cap,dtype=np.int64)]
        v=flatn[idx].astype(np.int64)
        coarse=np.unique(np.r_[[-133,133],np.arange(-128,129,16)]).astype(np.int64)
        Kc=np.floor_divide(v[None,:]-coarse[:,None]+RAD,STEP);sc=gamma_cost(Kc).sum(1);d0=int(coarse[int(np.argmin(sc))])
        fine=np.arange(max(-RAD,d0-16),min(RAD,d0+16)+1,dtype=np.int64)
        Kf=np.floor_divide(v[None,:]-fine[:,None]+RAD,STEP);sf=gamma_cost(Kf).sum(1);tab[int(j)]=int(fine[int(np.argmin(sf))])
    return tab,ctx,{'contexts':nc,'nonempty':used}

def build_dynamic(X,co,spec,tab):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Xi=np.rint(X).astype(np.int64);a=float(co[0]);b=np.asarray(co[1:],np.float32);gs,pc,diag,tseg=spec;P=2*pc+1
    for c in range(C):
      for t in range(NT):
        pred=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
        prev=int(K[c,t-1]) if t else 0;prev=max(-pc,min(pc,prev))+pc;left=int(K[c-1,t]) if c else 0;ls=0 if left<0 else (2 if left>0 else 1)
        q=((c//gs)*P+prev)*3+ls
        if diag:
          d0=int(K[c-1,t-1]) if c and t else 0;ds=0 if d0<0 else (2 if d0>0 else 1);q=q*3+ds
        tc=min(tseg-1,(t*tseg)//NT);q=q*tseg+tc;d=int(tab[q]);n=int(Xi[c,t])-pred-d;k=(n+RAD)//STEP;r=pred+d+STEP*k
        if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',spec,c,t))
        K[c,t]=k;R[c,t]=r
    return R,K

def decode_dynamic(K,co,spec,tab):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32);gs,pc,diag,tseg=spec;P=2*pc+1
    for c in range(C):
      for t in range(NT):
        pred=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
        prev=int(K[c,t-1]) if t else 0;prev=max(-pc,min(pc,prev))+pc;left=int(K[c-1,t]) if c else 0;ls=0 if left<0 else (2 if left>0 else 1)
        q=((c//gs)*P+prev)*3+ls
        if diag:
          d0=int(K[c-1,t-1]) if c and t else 0;ds=0 if d0<0 else (2 if d0>0 else 1);q=q*3+ds
        q=q*tseg+min(tseg-1,(t*tseg)//NT);R[c,t]=pred+int(tab[q])+STEP*int(K[c,t])
    return R

def side_bytes(spec,tab):return 6+2*len(tab)
def serialize(spec,tab):return struct.pack('<BBBBH',spec[0],spec[1],spec[2],spec[3],len(tab))+np.asarray(tab,dtype='<i2').tobytes()
def parse(bb):
    gs,pc,dg,ts,n=struct.unpack_from('<BBBBH',bb,0);tab=np.frombuffer(bb[6:6+2*n],dtype='<i2').copy();return (gs,pc,dg,ts),tab

def encode_fixed(K):
    stream=bytearray();entries={};rows={}
    for comp in cg.COMPONENTS:
      gr,W=rc.CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W);stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb);rows[comp]={'payload_bytes':len(bb),'bits':int(nb),'grammar':gr,'W':W}
    return bytes(stream),entries,rows

def main(path):
    with h5py.File(path,'r') as hf:
      d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0;base=rc.k_proxy(K0)
    screens=[];tables={}
    for spec in SPECS:
      tab,ctx,meta=fit_table(N,K0,spec);tables[spec]=tab;D=tab[ctx];Ka=np.floor_divide(N-D.astype(np.int64)+RAD,STEP);side=side_bytes(spec,tab);pr=float(gamma_cost(Ka).sum()/(C*NT)+8*side/(C*NT));row={'spec':list(spec),'contexts':len(tab),'side_bytes':side,'charged_fixed_predictor_proxy_bps':pr,'gain_proxy_bps':base-pr};screens.append(row);print(json.dumps({'screen':row}),flush=True)
    top=sorted(screens,key=lambda r:r['charged_fixed_predictor_proxy_bps'])[:3];exact=[]
    for row in top:
      spec=tuple(row['spec']);tab=tables[spec];R,K=build_dynamic(X,cod,spec,tab);side=side_bytes(spec,tab);pr=rc.k_proxy(K)+8*side/(C*NT);stream,entries,comps=encode_fixed(K);total=cg.OUTER_BYTES+len(model)+side+len(stream);me=float(np.max(np.abs(X-R.astype(np.float64))));er={'spec':list(spec),'contexts':len(tab),'side_bytes':side,'charged_recursive_proxy_bps':pr,'bytes':int(total),'delta_vs_new_incumbent':int(total-NEW_INC),'maxerr':me,'components':comps};exact.append(er);print(json.dumps({'exact':er}),flush=True)
    win=min(exact,key=lambda r:r['bytes']);spec=tuple(win['spec']);tab=tables[spec];R,K=build_dynamic(X,cod,spec,tab);side=serialize(spec,tab);spec2,tab2=parse(side);stream,entries,comps=encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=decode_dynamic(Kd,cod,spec2,tab2)
    if not np.array_equal(Rd,R):raise RuntimeError('R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
    out={'winner_spec':list(spec),'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_new_incumbent':int(total-NEW_INC),'gain_vs_new_incumbent':NEW_INC/total,'phase_side_bytes':len(side),'model_bytes':len(model),'component_stream_bytes':len(stream),'maxerr':me,'eps':eps,'screens':screens,'exact_candidates':exact,'components':comps,'scope':'Richer decoder-causal GCA phase-policy search. Phase is selected sample-by-sample from already-decoded K state plus public channel/time coordinates. Candidate tables are charged explicitly; top fixed-predictor screens are recursively materialized, physically component-coded, then winner is independently K-decoded and source-replayed under the unchanged hard error. Comparator is the PR649 exact 2,465,652-byte phase-policy incumbent.'};json.dump(out,open('imperial_gca_phase_policy_v2.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
