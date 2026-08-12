import json, sys
import numpy as np
import segyio
from scipy.spatial import cKDTree


def angle_dist(a,b):
    d=abs(a-b)%np.pi
    return min(d,np.pi-d)

def lattice_fit(P, theta1, theta2, nn_vecs):
    u1=np.array([np.cos(theta1),np.sin(theta1)])
    u2=np.array([np.cos(theta2),np.sin(theta2)])
    vals=[]
    for th,u in [(theta1,u1),(theta2,u2)]:
        cand=[]
        for v in nn_vecs:
            a=np.arctan2(v[1],v[0])%np.pi
            if angle_dist(a,th)<np.deg2rad(12):
                cand.append(abs(float(v@u)))
        cand=np.array([x for x in cand if x>1e-6])
        if cand.size<8: return None
        # nearest-neighbour vectors dominate; lower quartile suppresses 2x/3x jumps
        s=float(np.median(np.sort(cand)[:max(8,cand.size//2)]))
        vals.append(s)
    s1,s2=vals
    A=np.stack([u1,u2],axis=1)
    if abs(np.linalg.det(A))<0.15: return None
    uv=np.linalg.solve(A,P.T).T
    origin=uv.min(axis=0)
    ij=np.rint((uv-origin)/np.array([s1,s2])).astype(int)
    uniq=len({tuple(x) for x in ij.tolist()})
    # affine refit from inferred integer coordinates to surveyed XY
    H=np.c_[np.ones(len(P)),ij]
    coef=np.linalg.lstsq(H,P,rcond=None)[0]
    fit=H@coef
    err=np.linalg.norm(P-fit,axis=1)
    ni=int(ij[:,0].max()-ij[:,0].min()+1); nj=int(ij[:,1].max()-ij[:,1].min()+1)
    return {
        'theta1_deg':float(np.rad2deg(theta1)), 'theta2_deg':float(np.rad2deg(theta2)),
        'spacing1':s1,'spacing2':s2,'grid_i':ni,'grid_j':nj,'grid_cells':ni*nj,
        'unique_cells':uniq,'duplicate_points':int(len(P)-uniq),'occupancy':float(uniq/max(1,ni*nj)),
        'snap_rmse':float(np.sqrt(np.mean(err**2))),'snap_p95':float(np.quantile(err,.95)),'snap_max':float(err.max())
    }

def inspect(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.float64)
        gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.float64)
    groups={}
    for x,y in zip(gx,gy): groups[(int(x),int(y))]=groups.get((int(x),int(y)),0)+1
    P=np.asarray(list(groups),dtype=np.float64)
    cnt=np.asarray(list(groups.values()),dtype=int)
    Pc=P-P.mean(axis=0)
    cov=Pc.T@Pc/max(1,len(P)-1); w,V=np.linalg.eigh(cov); order=np.argsort(w)[::-1]; w=w[order];V=V[:,order]
    tree=cKDTree(P); d,ii=tree.query(P,k=min(9,len(P)))
    nn=d[:,1]
    med=float(np.median(nn)); cutoff=max(1e-9,2.2*med)
    vecs=[]
    for r in range(len(P)):
        for k in range(1,ii.shape[1]):
            if d[r,k]<=cutoff:
                v=P[ii[r,k]]-P[r]
                if np.linalg.norm(v)>1e-9: vecs.append(v)
    vecs=np.asarray(vecs)
    ang=np.mod(np.arctan2(vecs[:,1],vecs[:,0]),np.pi)
    bins=180; hist,edges=np.histogram(ang,bins=bins,range=(0,np.pi))
    smooth=np.convolve(np.r_[hist[-3:],hist,hist[:3]],[1,2,3,4,3,2,1],mode='valid')
    peaks=[]
    for idx in np.argsort(smooth)[::-1]:
        th=(idx+.5)*np.pi/bins
        if all(angle_dist(th,p[0])>np.deg2rad(12) for p in peaks):
            peaks.append((th,int(smooth[idx])))
        if len(peaks)>=6: break
    fits=[]
    for a in range(min(4,len(peaks))):
        for b in range(a+1,min(6,len(peaks))):
            if np.deg2rad(20)<angle_dist(peaks[a][0],peaks[b][0])<np.deg2rad(160):
                q=lattice_fit(P,peaks[a][0],peaks[b][0],vecs)
                if q: fits.append(q)
    fits.sort(key=lambda q:(q['duplicate_points'],q['snap_rmse'],q['grid_cells']))
    mode=int(np.bincount(cnt).argmax())
    return {
      'file':path,'receivers':len(P),'traces':len(gx),'component_mode':mode,'component_mode_fraction':float(np.mean(cnt==mode)),
      'bbox':[float(P[:,0].min()),float(P[:,0].max()),float(P[:,1].min()),float(P[:,1].max())],
      'nn_median':med,'nn_p10':float(np.quantile(nn,.1)),'nn_p90':float(np.quantile(nn,.9)),
      'pca_eigenvalues':[float(x) for x in w], 'pca_axis0_deg':float(np.rad2deg(np.arctan2(V[1,0],V[0,0])%np.pi)),
      'direction_peaks':[{'deg':float(np.rad2deg(t)),'score':s} for t,s in peaks],
      'best_lattice_fits':fits[:8]
    }

out={'shots':[inspect(p) for p in sys.argv[1:]]}
print(json.dumps(out,indent=2),flush=True)
json.dump(out,open('soda_geometry_diag.json','w'),indent=2)
