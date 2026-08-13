import json,sys,math
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_decoder_phase_automaton as m

L=g.L;KNN=64;ALPHA_NUM=np.asarray([-1,1,2,3],np.int16) # alpha=num/2
NTARGET=512

def decoded_prefix_centers(R0,co):
    V=[]
    for c in range(g.C):
        for t in range(g.P,g.TRAIN-g.L+1,g.L):
            base=g.openloop(R0[c,t-g.P:t],co);V.append(R0[c,t:t+g.L].astype(np.float64)-base)
    return np.asarray(V,np.float32)

def heldout(X,R0,co,eps):
    V=[]
    for c in g.TARGET_CH:
        state=R0[c,-g.P:].copy()
        for t in range(g.TRAIN,g.END,g.L):
            base=g.openloop(state,co);src=X[c,t:t+g.L];V.append(src-base)
            for q in range(g.L):
                vv=float(co[-1])
                for j in range(g.P):vv+=float(co[j])*state[-1-j]
                pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/g.STEP));rr=pred+g.STEP*k
                if abs(float(src[q])-rr)>eps*(1+1e-10):raise RuntimeError('incumbent hard')
                state[:-1]=state[1:];state[-1]=rr
    V=np.asarray(V,np.float32);sel=np.linspace(0,len(V)-1,NTARGET,dtype=np.int64);return V,V[sel],sel

def build_atlas(C):
    tree=cKDTree(C,compact_nodes=True,balanced_tree=True);dist,idx=tree.query(C,k=KNN+1,p=np.inf,workers=1);idx=idx[:,1:]
    N=len(C);out=np.empty((N*KNN*len(ALPHA_NUM),L),np.float32);owner=np.empty((N*KNN*len(ALPHA_NUM),3),np.int32);p=0
    for a in range(0,N,256):
        aa=np.arange(a,min(a+256,N));A=C[aa]
        B=C[idx[aa]]
        D=B-A[:,None,:]
        for qi,num in enumerate(ALPHA_NUM):
            X=A[:,None,:]+(float(num)/2.0)*D;z=X.reshape(-1,L);n=len(z);out[p:p+n]=np.rint(z).astype(np.float32)
            ii=np.repeat(aa,KNN);rr=np.tile(np.arange(KNN,dtype=np.int32),len(aa));owner[p:p+n,0]=ii;owner[p:p+n,1]=rr;owner[p:p+n,2]=qi;p+=n
    if p!=len(out):raise RuntimeError((p,len(out)))
    return out,owner,idx,dist[:,1:]

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps);C=decoded_prefix_centers(R0,co);HV,H,sel=heldout(X,R0,co,eps)
    atlas,owner,nbr,nbrdist=build_atlas(C);tree=cKDTree(atlas,compact_nodes=True,balanced_tree=True)
    hitidx=[];counts=[];nearest=[]
    for i,y in enumerate(H):
        ids=tree.query_ball_point(y,r=eps,p=np.inf);counts.append(len(ids));hitidx.append(min(ids) if ids else None);nearest.append(float(tree.query(y,k=1,p=np.inf)[0]))
        if i%64==0:print(json.dumps({'target':i,'hits':len(ids),'nearest_linf':nearest[-1]}),flush=True)
    hits=np.asarray([x is not None for x in hitidx]);F=float(np.mean(hits));first=[]
    for q in hitidx:
        if q is not None:first.append(owner[int(q)].tolist())
    szb=g.szrun(X[g.TARGET_CH,g.TRAIN:g.END],eps);szbps=8*szb[0]/(len(g.TARGET_CH)*(g.END-g.TRAIN));target=szbps/2
    Ncenter=len(C);center_bits=int(math.ceil(math.log2(Ncenter)));variant_bits=int(math.ceil(math.log2(KNN)))+int(math.ceil(math.log2(len(ALPHA_NUM))));nominal=center_bits+variant_bits
    out={'global_std':std,'eps':eps,'ar_order':g.P,'block_length':L,'decoder_known_prefix_centers':Ncenter,'nearest_neighbors_per_center':KNN,'alpha_numerators_over_2':ALPHA_NUM.tolist(),'implicit_codewords':int(len(atlas)),'center_id_bits':center_bits,'neighbor_rank_bits':int(math.ceil(math.log2(KNN))),'alpha_bits':int(math.ceil(math.log2(len(ALPHA_NUM)))),'nominal_index_bits_per_block':nominal,'nominal_index_bps':nominal/L,'prefix_neighbor_linf_median':float(np.median(nbrdist)),'prefix_neighbor_linf_p90':float(np.percentile(nbrdist,90)),'sampled_targets':len(H),'coverage_fraction':F,'mean_hits_per_target':float(np.mean(counts)),'median_hits_per_target':float(np.median(counts)),'nearest_linf_median':float(np.median(nearest)),'nearest_linf_p90':float(np.percentile(nearest,90)),'matched_sz3_bps':szbps,'two_x_target_bps':target,'nominal_index_bps_over_2x_target':nominal/L/target,'first_hit_owner_examples':first[:16],'scope':'Prefix-affine atlas covering diagnostic, NOT yet a sequential codec. The shared AR32 and legal reconstructed prefix are decoder-known. Every nonoverlapping decoded prefix residual block becomes a zero-metadata 8-D prototype. The decoder deterministically rebuilds a 64-nearest-neighbor graph in L-infinity. Each prototype/neighbour chord generates four integer affine candidates at alpha=-0.5,0.5,1.0,1.5. Thus roughly four million synthetic codewords require no stored vector dictionary; a codeword can be identified by center ID + 6-bit neighbour rank + 2-bit alpha selector (~22 bits/8 samples nominal). Exact cKDTree queries test fixed-incumbent held-out residual boxes for coverage and nearest distance. Because target AR state is not advanced using atlas hits in this diagnostic, coverage is only a geometry gate. If coverage is material, the next branch will implement the sequential decoder-real atlas codec with escapes and actual entropy-coded IDs. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_prefix_affine_atlas_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
