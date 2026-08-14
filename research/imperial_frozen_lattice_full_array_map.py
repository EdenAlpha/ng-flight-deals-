import glob,json,sys
import h5py,numpy as np
import imperial_frozen_lattice_layout_gate as fg

C=128
NT=30000
TB=1024
BLOCKS=54
PER_SLOT=6


def run_slot(path,slot):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=fg.a.m.stats(d);eps=.1*gstd;step=2.0*eps
        rows=[]
        b0=slot*PER_SLOT;b1=min(BLOCKS,b0+PER_SLOT)
        for cb in range(b0,b1):
            c0=cb*C
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            Q=np.rint(X/step).astype(np.int32)
            R0=Q.astype(np.float64)*step
            qerr=float(np.max(np.abs(X-R0)))
            if qerr>eps*(1+3e-6):raise RuntimeError((cb,'nearest hard',qerr,eps))

            Td=fg.transform(Q,'time_delta')
            change=float(np.mean(Td!=0))
            cands=[]
            for tr in ('direct','time_delta'):
                K=Q if tr=='direct' else Td
                for codec in (fg.dense_codec,fg.sparse_codec):
                    n,diag=codec(K);n+=1
                    Qd=fg.inverse(K,tr)
                    if not np.array_equal(Qd,Q):raise RuntimeError((cb,tr,'inverse'))
                    me=float(np.max(np.abs(X-Qd.astype(np.float64)*step)))
                    if me>eps*(1+3e-6):raise RuntimeError((cb,tr,'hard',me,eps))
                    q={'transform':tr,'bytes':int(n),'bps':8*n/X.size,'maxerr':me,
                       'field_zero_fraction':float(np.mean(K==0))}
                    q.update(diag);cands.append(q)
            best=min(cands,key=lambda q:q['bytes'])

            sz=0
            for t0 in range(0,NT,TB):
                n,_=fg.a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
            hybrid=min(sz,best['bytes'])
            row={'cb':cb,'c0':c0,'samples':int(X.size),'eps':float(eps),'step':float(step),
                 'temporal_change_fraction':change,'source_lattice_zero_fraction':float(np.mean(Q==0)),
                 'frozen':best,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,
                 'frozen_gain_vs_sz3':float(sz/best['bytes']),
                 'frozen_meets_2x_sz3':bool(best['bytes']*2<=sz),
                 'hybrid_bytes':int(hybrid),'hybrid_gain_vs_sz3':float(sz/hybrid),
                 'candidates':cands}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'slot':slot,'blocks':[b0,b1],'global_std':float(gstd),'eps':float(eps),'rows':rows,
             'scope':'Full-array structural transfer of the raw-FORGE frozen-state mechanism. Each complete 128x30000 Imperial block is reconstructed on the legal 2*epsilon source lattice. Direct Q and temporal-delta fields are losslessly tested as dense and sparse-mask/value Zstd-22 streams. Every payload is byte-decompressed and verified, the exact inverse is checked, and source max error is reverified. Matched SZ3 is rerun on identical samples. The main diagnostic is temporal lattice-state change density and the per-block oracle hybrid min(frozen,SZ3). No AI. Draft/do not merge.'}
        json.dump(out,open(f'imperial_frozen_lattice_full_{slot}.json','w'),indent=2)


def aggregate():
    rows=[]
    for p in sorted(glob.glob('imperial_frozen_lattice_full_*.json')):
        if p.endswith('_aggregate.json'):continue
        rows.extend(json.load(open(p))['rows'])
    rows=sorted(rows,key=lambda r:r['cb'])
    if len(rows)!=BLOCKS:raise RuntimeError(('expected blocks',BLOCKS,'got',len(rows)))
    sz=sum(r['sz3_bytes'] for r in rows);fr=sum(r['frozen']['bytes'] for r in rows);hy=sum(r['hybrid_bytes'] for r in rows)
    samples=sum(r['samples'] for r in rows)
    changes=np.array([r['temporal_change_fraction'] for r in rows],np.float64)
    gains=np.array([r['frozen_gain_vs_sz3'] for r in rows],np.float64)
    out={'blocks':len(rows),'samples':samples,'sz3_bytes':sz,'sz3_bps':8*sz/samples,
         'frozen_bytes':fr,'frozen_bps':8*fr/samples,'frozen_gain_vs_sz3':sz/fr,
         'oracle_hybrid_bytes':hy,'oracle_hybrid_bps':8*hy/samples,'oracle_hybrid_gain_vs_sz3':sz/hy,
         'strict_2x_target_bytes':sz/2.0,'bytes_above_2x_target':hy-sz/2.0,
         'fraction_reduction_still_needed_from_hybrid':1.0-(sz/2.0)/hy,
         'blocks_frozen_beats_sz3':sum(r['frozen']['bytes']<r['sz3_bytes'] for r in rows),
         'blocks_frozen_meets_2x_sz3':sum(r['frozen_meets_2x_sz3'] for r in rows),
         'change_fraction_min':float(changes.min()),'change_fraction_median':float(np.median(changes)),
         'change_fraction_mean':float(changes.mean()),'change_fraction_max':float(changes.max()),
         'best_frozen_gain':float(gains.max()),'worst_frozen_gain':float(gains.min()),'rows':rows}
    json.dump(out,open('imperial_frozen_lattice_full_aggregate.json','w'),indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)


if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='aggregate':aggregate()
    else:run_slot(sys.argv[1],int(sys.argv[2]))
