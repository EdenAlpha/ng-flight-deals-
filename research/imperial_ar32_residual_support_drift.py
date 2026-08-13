import json,sys
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_decoder_phase_automaton as m

L=g.L

def percentile_dict(a):
    a=np.asarray(a,float);return {str(p):float(np.percentile(a,p)) for p in (10,25,50,75,90,95,99)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps);TV=g.train_vectors(X,R0,co);HV,H,sel=g.heldout_vectors(X,R0,co,eps)
    # All-region prefix dictionary versus all held-out residual blocks.
    tt=cKDTree(TV,compact_nodes=True,balanced_tree=True);dpre,ipre=tt.query(HV,k=1,p=np.inf)
    # Intrinsic target support: nearest OTHER held-out block. k=2 because self is zero.
    ht=cKDTree(HV,compact_nodes=True,balanced_tree=True);d2,i2=ht.query(HV,k=2,p=np.inf);dself=d2[:,1]
    # Exact compatibility neighborhoods: two source epsilon boxes intersect iff distance<=2eps.
    counts2=np.asarray(ht.query_ball_point(HV,r=2*eps,p=np.inf,return_length=True),np.int64)-1
    countse=np.asarray(ht.query_ball_point(HV,r=eps,p=np.inf,return_length=True),np.int64)-1
    # Same-channel prefix dictionaries and corresponding held-out subsequences.
    ntrain=(g.TRAIN-g.P-g.L+1)//g.L + 1
    # Reconstruct exact per-channel train/heldout lists to avoid relying on concatenation offsets.
    same=[]
    for c in g.TARGET_CH:
        A=[]
        for t in range(g.P,g.TRAIN-g.L+1,g.L):A.append(X[c,t:t+g.L]-g.openloop(R0[c,t-g.P:t],co))
        A=np.asarray(A,float);tree=cKDTree(A,compact_nodes=True,balanced_tree=True)
        state=R0[c,-g.P:].copy();B=[]
        for t in range(g.TRAIN,g.END,g.L):
            base=g.openloop(state,co);src=X[c,t:t+g.L];B.append(src-base)
            for q in range(g.L):
                vv=float(co[-1])
                for j in range(g.P):vv+=float(co[j])*state[-1-j]
                pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/g.STEP));rr=pred+g.STEP*k;state[:-1]=state[1:];state[-1]=rr
        B=np.asarray(B,float);dd,_=tree.query(B,k=1,p=np.inf);same.extend(dd.tolist())
    same=np.asarray(same)
    out={'global_std':std,'eps':eps,'diameter_2eps':2*eps,'ar_order':g.P,'block_length':L,'training_vectors':len(TV),'heldout_vectors':len(HV),'prefix_to_heldout_nearest_linf':{'percentiles':percentile_dict(dpre),'fraction_within_eps':float(np.mean(dpre<=eps)),'fraction_within_2eps':float(np.mean(dpre<=2*eps))},'same_channel_prefix_to_heldout_nearest_linf':{'percentiles':percentile_dict(same),'fraction_within_eps':float(np.mean(same<=eps)),'fraction_within_2eps':float(np.mean(same<=2*eps))},'heldout_to_other_heldout_nearest_linf':{'percentiles':percentile_dict(dself),'fraction_within_eps':float(np.mean(dself<=eps)),'fraction_within_2eps':float(np.mean(dself<=2*eps))},'heldout_box_intersection_degree':{'fraction_with_any_other_intersecting_box':float(np.mean(counts2>0)),'median_other_intersections':float(np.median(counts2)),'p90_other_intersections':float(np.percentile(counts2,90)),'max_other_intersections':int(counts2.max()),'fraction_with_other_source_point_inside_own_eps_box':float(np.mean(countse>0))},'norms':{'train_rms_median':float(np.median(np.sqrt(np.mean(TV*TV,axis=1)))),'heldout_rms_median':float(np.median(np.sqrt(np.mean(HV*HV,axis=1)))),'train_coordinate_std':float(TV.std()),'heldout_coordinate_std':float(HV.std())},'scope':'Residual-support drift/geometry audit, not a compression claim. Same shared AR32 and open-loop 8-D residual definitions as PR345/348. Exact Chebyshev nearest-neighbor searches compare real prefix residual vectors against all held-out residual vectors, same-channel prefix support, and held-out blocks against other held-out blocks. Two epsilon-boxes can share some reconstruction codeword only if their L-infinity source separation is <=2epsilon, so held-out neighborhood degrees directly measure finite-sample box-intersection structure. This separates prefix/model distribution shift from intrinsic isolation of target boxes. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_residual_support_drift.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
