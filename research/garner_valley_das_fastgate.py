import json,math,os,sys
import numpy as np,segyio
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.garner_valley_das_full_benchmark import lattice_tile,checker_tile,encode_tile,sz3_best,SPACE,TIME,SAFETY

def main(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    std=float(A.std(dtype=np.float64));eps=.1*std;internal=eps*SAFETY
    cps=sorted(set([0,max(0,(ntr-SPACE)//2),max(0,ntr-SPACE)]));tps=sorted(set([0,max(0,(ns-TIME)//2),max(0,ns-TIME)]));rows=[]
    for c0 in cps:
        for t0 in tps:
            W=np.ascontiguousarray(A[c0:c0+SPACE,t0:t0+TIME]);AT=np.ascontiguousarray(W.T)
            sb,so,sme=sz3_best(AT,eps);lb,lme,lnz,lrep=lattice_tile(W,eps,internal);cb,cme,cd=checker_tile(W,eps,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob)
            if pme>eps*(1+5e-6):raise RuntimeError(('spectral hard',pme,eps,c0,t0))
            n=W.size;rows.append({'c0':c0,'t0':t0,'sz3_bytes':sb,'sz3_bps':8*sb/n,'sz3_orientation':so,'lattice_bytes':lb,'lattice_bps':8*lb/n,'lattice_gain':sb/lb,'lattice_transition_nonzero':lnz,'checker_bytes':cb,'checker_bps':8*cb/n,'checker_gain':sb/cb,'checker_correction_nonzero':cd['correction_nonzero'],'spectral_bytes':pb,'spectral_bps':8*pb/n,'spectral_gain':sb/pb,'spectral_correction_nonzero':pd['correction_nonzero_fraction'],'maxerr':{'sz3':sme,'lattice':lme,'checker':cme,'spectral':pme}})
    S=sum(r['sz3_bytes'] for r in rows);samples=SPACE*TIME*len(rows);agg=[]
    for k in ('lattice','checker','spectral'):
        b=sum(r[k+'_bytes'] for r in rows);agg.append({'method':k,'bytes':b,'sz3_bytes':S,'bps':8*b/samples,'gain_vs_sz3':S/b,'min_tile_gain':min(r[k+'_gain'] for r in rows),'median_tile_gain':float(np.median([r[k+'_gain'] for r in rows])),'max_tile_gain':max(r[k+'_gain'] for r in rows)})
    agg.sort(key=lambda r:r['bytes']);out={'shape':[ntr,ns],'std':std,'eps':eps,'channel_positions':cps,'time_positions':tps,'aggregate':agg,'rows':rows,'scope':'Nine precommitted full-resolution tiles spanning the complete Garner DAS channel/time extent. Epsilon is 10% std of the entire 1,984x12,600 DAS array, not per tile. Same methods/fairness as full PR259; diagnostic only.'};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('garner_valley_das_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
