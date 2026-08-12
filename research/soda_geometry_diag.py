import json, sys
import numpy as np
import segyio
from scipy.spatial import cKDTree


def inspect(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64)
        gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={}
    invalid_traces=0
    for x,y in zip(gx,gy):
        if (x==0 and y==0): invalid_traces+=1; continue
        groups[(int(x),int(y))]=groups.get((int(x),int(y)),0)+1
    P=np.asarray(list(groups),dtype=np.float64)
    cnt=np.asarray(list(groups.values()),dtype=int)
    mode=int(np.bincount(cnt).argmax())

    Pc=P-P.mean(axis=0)
    cov=Pc.T@Pc/max(1,len(P)-1)
    w,V=np.linalg.eigh(cov); order=np.argsort(w)[::-1]; w=w[order]; V=V[:,order]
    u=V[:,0]; v=V[:,1]
    t=Pc@u; cross=Pc@v
    order_t=np.argsort(t); ts=t[order_t]; ds=np.diff(ts)
    pos=ds[ds>1e-9]
    med_step=float(np.median(pos)) if pos.size else 0.0
    idx=np.rint((t-t.min())/max(med_step,1e-30)).astype(int)
    fit_t=t.min()+idx*med_step
    along_res=t-fit_t

    tree=cKDTree(P); d,ii=tree.query(P,k=min(5,len(P)))
    nn=d[:,1]
    vec=P[ii[:,1]]-P
    ang=np.mod(np.arctan2(vec[:,1],vec[:,0]),np.pi)
    # circular mean for line orientation: double angles to identify theta and theta+pi
    z=np.mean(np.exp(2j*ang)); theta=(0.5*np.angle(z))%np.pi
    concentration=float(abs(z))

    uniq_idx=len(np.unique(idx)); span=int(idx.max()-idx.min()+1)
    line_rms=float(np.sqrt(np.mean(cross**2)))
    line_p95=float(np.quantile(np.abs(cross),.95))
    line_span=float(t.max()-t.min())
    return {
      'file':path,'receivers_valid':len(P),'traces_total':len(gx),'invalid_zero_coord_traces':invalid_traces,
      'component_mode':mode,'component_mode_fraction':float(np.mean(cnt==mode)),
      'bbox_valid':[float(P[:,0].min()),float(P[:,0].max()),float(P[:,1].min()),float(P[:,1].max())],
      'pca_eigenvalues':[float(x) for x in w],
      'pca_line_angle_deg':float(np.rad2deg(np.arctan2(u[1],u[0])%np.pi)),
      'pca_anisotropy':float(w[0]/max(w[1],1e-30)),
      'line_span':line_span,'line_cross_rms':line_rms,'line_cross_p95':line_p95,'cross_to_span':float(line_rms/max(line_span,1e-30)),
      'nn_median':float(np.median(nn)),'nn_p10':float(np.quantile(nn,.1)),'nn_p90':float(np.quantile(nn,.9)),
      'nn_direction_deg':float(np.rad2deg(theta)),'nn_direction_concentration':concentration,
      'projected_step_median':med_step,'projected_step_p10':float(np.quantile(pos,.1)) if pos.size else 0.0,'projected_step_p90':float(np.quantile(pos,.9)) if pos.size else 0.0,
      'inferred_line_sites':span,'occupied_line_sites':uniq_idx,'line_occupancy':float(uniq_idx/max(span,1)),
      'along_snap_rms':float(np.sqrt(np.mean(along_res**2))),'along_snap_p95':float(np.quantile(np.abs(along_res),.95))
    }

out={'shots':[inspect(p) for p in sys.argv[1:]]}
print(json.dumps(out,indent=2),flush=True)
json.dump(out,open('soda_geometry_diag.json','w'),indent=2)
