from pathlib import Path
p=Path('research/soda_lattice_kxyf.py')
s=p.read_text()
old="""    li-=li.min();si-=si.min();pairs=list(zip(li.tolist(),si.tolist()))
    return li,si,{'line_angle_deg':float(np.rad2deg(theta)),'direction_concentration':float(abs(z)),'along_step':along_step,'cross_step':cross_step,'n_lines':int(li.max()+1),'n_stations':int(si.max()+1),'grid_cells':int((li.max()+1)*(si.max()+1)),'occupied_cells':len(set(pairs)),'occupancy':float(len(set(pairs))/((li.max()+1)*(si.max()+1))),'duplicates':int(len(P)-len(set(pairs))),'nn_median':nnmed}
"""
new="""    li-=li.min();si-=si.min()
    # A survey point can land exactly on a rounding boundary. Resolve the very
    # rare collision by moving only the later point to the nearest unoccupied
    # station on the same inferred receiver line. The choice minimizes the
    # physical along-line coordinate error, so every real receiver survives.
    seen=set()
    for idx in np.argsort(along):
        l=int(li[idx]); q=int(si[idx])
        if (l,q) in seen:
            choices=[]
            for dq in (-1,1,-2,2,-3,3,-4,4):
                qq=q+dq
                if qq>=0 and (l,qq) not in seen:
                    choices.append((abs(float(along[idx]-(a0+qq*along_step))),qq))
            if not choices:
                raise RuntimeError('unable to resolve lattice collision')
            si[idx]=min(choices)[1]; q=int(si[idx])
        seen.add((l,q))
    pairs=list(zip(li.tolist(),si.tolist()))
    return li,si,{'line_angle_deg':float(np.rad2deg(theta)),'direction_concentration':float(abs(z)),'along_step':along_step,'cross_step':cross_step,'n_lines':int(li.max()+1),'n_stations':int(si.max()+1),'grid_cells':int((li.max()+1)*(si.max()+1)),'occupied_cells':len(set(pairs)),'occupancy':float(len(set(pairs))/((li.max()+1)*(si.max()+1))),'duplicates':int(len(P)-len(set(pairs))),'nn_median':nnmed}
"""
if old not in s:
    raise SystemExit('collision patch anchor missing')
p.write_text(s.replace(old,new))
print('collision-safe lattice patch applied')
