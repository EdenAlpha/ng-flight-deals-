import json,sys
import h5py,numpy as np
import imperial_ar32_halfstep_control_channel as h
import imperial_decoder_phase_automaton as m
import imperial_ar32_hadamard_control_code as w

C0=512;C=128;P=32;TRAIN=1024;END=5120;COARSE=256;HALF=128
BETAS=(0.0,0.12,0.30)
CHANNELS=(0,16,32,48,64,80,96,112)

def free_local(X,co,R0,beta):
    T=X.shape[1]-TRAIN;state=R0[:,-P:].astype(np.int64).copy();prevj=np.zeros(C,np.int64);J=np.empty((C,T),np.int64);B=np.empty((C,T),np.uint8);R=np.empty((C,T),np.int64)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);x=X[:,TRAIN+u];j0=np.rint((x-pred)/COARSE).astype(np.int64);j1=np.rint((x-pred-HALF)/COARSE).astype(np.int64)
        c0=np.log2(1+np.abs(j0).astype(float));c1=np.log2(1+np.abs(j1).astype(float))
        if beta:
            c0+=beta*np.log2(1+np.abs(j0-prevj).astype(float));c1+=beta*np.log2(1+np.abs(j1-prevj).astype(float))
        b=(c1<c0);j=np.where(b,j1,j0);rr=pred+COARSE*j+HALF*b.astype(np.int64);J[:,u]=j;B[:,u]=b;R[:,u]=rr;prevj=j;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return J,B,R

def reconstruct(J,B,co,R0):
    T=J.shape[1];state=R0[:,-P:].astype(np.int64).copy();R=np.empty_like(J,np.int64)
    for u in range(T):
        v=np.full(J.shape[0],float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);rr=pred+COARSE*J[:,u]+HALF*B[:,u].astype(np.int64);R[:,u]=rr;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0,J0=h.fit_prefix(X);G,GR=w.greedy_all(X,co,R0);gbytes,Gd,greps=w.encode_j_frames(G);sz=0
    for t0 in range(TRAIN,END,1024):
        sb,_=m.szrun(X[:,t0:min(t0+1024,END)],eps);sz+=sb
    rows=[]
    for beta in BETAS:
        J,B,R=free_local(X,co,R0,beta);jb,Jd,reps=w.encode_j_frames(J);Rd=reconstruct(Jd,B,co,R0);me=float(np.max(np.abs(X[:,TRAIN:END]-Rd)))
        if me>eps*(1+1e-10) or not np.array_equal(Rd,R):raise RuntimeError(('local hard',beta,me))
        rows.append({'kind':'all128_free_local','beta':beta,'oracle_bytes':mb+jb,'oracle_bps':8*(mb+jb)/J.size,'innovation_bytes':jb,'gain_vs_greedy':(mb+gbytes)/(mb+jb),'gain_vs_sz3_if_control_free':sz/(mb+jb),'fraction_of_2x_target_bytes':(mb+jb)/(sz/2),'B_one_fraction':float(np.mean(B)),'B_transition_fraction_time':float(np.mean(B[:,1:]!=B[:,:-1])),'j_zero_fraction':float(np.mean(J==0)),'j_std':float(J.std()),'maxerr':me,'reps':reps})
    nll=h.make_nll(J0);target=X[:,TRAIN:END];JJ=[];BB=[];GG=[]
    for c in CHANNELS:
        g,_=h.greedy(target[c],co,R0[c]);GG.append(g);j,b,st=h.beam_channel(target[c],co,R0[c],J0[c],eps,0.0,0.0,nll);JJ.append(j);BB.append(b)
    GG=np.stack(GG);JJ=np.stack(JJ);BB=np.stack(BB);gb,_,_=h.kframe(GG);jb,jrep,Jd=h.kframe(JJ);RR=np.stack([h.reconstruct(Jd[i],BB[i],co,R0[c]) for i,c in enumerate(CHANNELS)]);me=float(np.max(np.abs(target[list(CHANNELS)]-RR)))
    if me>eps*(1+1e-10):raise RuntimeError(('beam hard',me))
    rows.append({'kind':'eight_channel_free_beam','beta':None,'oracle_bytes':jb,'oracle_bps':8*jb/JJ.size,'innovation_bytes':jb,'greedy_bytes':gb,'gain_vs_greedy':gb/jb,'B_one_fraction':float(np.mean(BB)),'B_transition_fraction_time':float(np.mean(BB[:,1:]!=BB[:,:-1])),'j_zero_fraction':float(np.mean(JJ==0)),'j_std':float(JJ.std()),'maxerr':me,'rep':jrep})
    allrows=[r for r in rows if r['kind']=='all128_free_local'];best=min(allrows,key=lambda x:x['oracle_bytes'])
    out={'global_std':std,'eps':eps,'ar_order':P,'target_interval':[TRAIN,END],'hard_channels':[C0,C0+C-1],'baseline':{'bytes':mb+gbytes,'bps':8*(mb+gbytes)/G.size,'innovation_bytes':gbytes,'sz3_bytes':sz,'sz3_bps':8*sz/G.size,'two_x_target_bytes':sz/2,'two_x_target_bps':4*sz/G.size},'best_free_all128':best,'rows':rows,'scope':'Deliberately impossible ceiling test for half-step distortion control. The persistent AR32 model and held-out hard-region target are unchanged. Every sample may use R=P+256J+128B. In the all-128-channel oracle, B is chosen independently at each sample under fixed local coarse-innovation costs and then GIVEN TO THE DECODER FOR ZERO BITS; only actual self-decoding J bytes and the AR model are counted. A second eight-channel oracle runs the existing width-64 future-state beam with B pulse/switch penalties set to zero and again charges zero B bytes. Both exact trajectories are regenerated and hard-error verified. These are NOT codec claims: they upper-bound what any B coding scheme could plausibly recover under these search families. If even free B remains far above half-SZ3 bytes, coded half-step control is structurally incapable of the 2x target.'}
    print(json.dumps({'baseline':out['baseline'],'best_free_all128':best,'beam':[r for r in rows if r['kind']=='eight_channel_free_beam'][0]},indent=2),flush=True);json.dump(out,open('imperial_ar32_free_control_oracle.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
