import json, sys
import numpy as np
import segyio
from scipy.spatial import cKDTree


def inspect(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64)
        gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={}; invalid=0
    for x,y in zip(gx,gy):
        if x==0 and y==0: invalid+=1; continue
        groups[(int(x),int(y))]=groups.get((int(x),int(y)),0)+1
    P=np.asarray(list(groups),dtype=np.float64); cnt=np.asarray(list(groups.values()),dtype=int)
    mode=int(np.bincount(cnt).argmax())

    tree=cKDTree(P); d,ii=tree.query(P,k=min(5,len(P)))
    nn=d[:,1]; vec=P[ii[:,1]]-P
    ang=np.mod(np.arctan2(vec[:,1],vec[:,0]),np.pi)
    z=np.mean(np.exp(2j*ang)); theta=(0.5*np.angle(z))%np.pi; concentration=float(abs(z))
    u=np.array([np.cos(theta),np.sin(theta)]); v=np.array([-u[1],u[0]])
    along=P@u; cross=P@v
    nnmed=float(np.median(nn))

    # Cluster parallel receiver lines in the cross-line coordinate. Survey jitter is
    # much smaller than the ~669-unit along-line receiver spacing.
    order=np.argsort(cross); eps=.35*nnmed; clusters=[]; cur=[int(order[0])]
    for a,b in zip(order[:-1],order[1:]):
        if cross[b]-cross[a] > eps:
            clusters.append(cur); cur=[]
        cur.append(int(b))
    clusters.append(cur)
    # Very small singleton clusters can be stray/bad coordinate groups; retain and report them.
    centers=np.array([np.median(cross[c]) for c in clusters]); cord=np.argsort(centers)
    clusters=[clusters[i] for i in cord]; centers=centers[cord]

    # Estimate common along-line station interval from consecutive positions within lines.
    diffs=[]
    for c in clusters:
        q=np.sort(along[c]); dd=np.diff(q); diffs.extend(dd[(dd>.4*nnmed)&(dd<1.6*nnmed)].tolist())
    step=float(np.median(diffs)) if diffs else nnmed
    a0=float(along.min()); station=np.rint((along-a0)/step).astype(int)
    line=np.empty(len(P),int)
    for li,c in enumerate(clusters): line[c]=li
    pairs={(int(line[i]),int(station[i])) for i in range(len(P))}
    nline=len(clusters); nstation=int(station.max()-station.min()+1)
    counts=[len(c) for c in clusters]
    # Fit surveyed XY as an affine function of inferred integer lattice coords.
    H=np.c_[np.ones(len(P)),line,station]; coef=np.linalg.lstsq(H,P,rcond=None)[0]; fit=H@coef
    err=np.linalg.norm(P-fit,axis=1)
    cross_gaps=np.diff(centers) if len(centers)>1 else np.array([])

    return {
      'file':path,'receivers_valid':len(P),'traces_total':len(gx),'invalid_zero_coord_traces':invalid,
      'component_mode':mode,'component_mode_fraction':float(np.mean(cnt==mode)),
      'nn_median':nnmed,'nn_p10':float(np.quantile(nn,.1)),'nn_p90':float(np.quantile(nn,.9)),
      'line_angle_deg':float(np.rad2deg(theta)),'line_direction_concentration':concentration,
      'line_cluster_eps':eps,'n_receiver_lines':nline,'line_counts_min':int(min(counts)),'line_counts_median':float(np.median(counts)),'line_counts_max':int(max(counts)),
      'crossline_gap_median':float(np.median(cross_gaps)) if cross_gaps.size else 0.0,'crossline_gap_min':float(cross_gaps.min()) if cross_gaps.size else 0.0,
      'station_step':step,'n_station_sites':nstation,'occupied_lattice_cells':len(pairs),'grid_cells':nline*nstation,'grid_occupancy':float(len(pairs)/max(1,nline*nstation)),
      'duplicate_lattice_cells':int(len(P)-len(pairs)),
      'affine_lattice_rmse':float(np.sqrt(np.mean(err**2))),'affine_lattice_p95':float(np.quantile(err,.95)),
      'line_centers':[float(x) for x in centers], 'line_counts':[int(x) for x in counts]
    }

out={'shots':[inspect(p) for p in sys.argv[1:]]}
print(json.dumps(out,indent=2),flush=True)
json.dump(out,open('soda_geometry_diag.json','w'),indent=2)
