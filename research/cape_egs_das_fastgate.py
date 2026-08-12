import json,math,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from research.cape_egs_das_benchmark import numeric_2d,choose_axes,read_block,global_stats,lattice_tile,checker_tile,sz3_best,encode_tile,SAFETY,SPACE,TIME

def main(path):
    with h5py.File(path,'r') as f:
        best,cands=numeric_2d(f);native,name,shape,dtype=best;d=f[name];ta,ca=choose_axes(shape);T=shape[ta];C=shape[ca]
        mean,std,n=global_stats(d,ta,T,C);eps=.1*std;internal=eps*SAFETY
        tp=sorted(set([0,max(0,(T-TIME)//2),max(0,T-TIME)]));span=max(0,C-6-SPACE);cp=sorted(set([6,6+span//2,max(6,C-SPACE)]))
        rows=[]
        for t0 in tp:
            for c0 in cp:
                A=read_block(d,ta,t0,min(T,t0+TIME),c0,min(C,c0+SPACE)).astype(np.float32,copy=False);W=A.T;sb,so,sme=sz3_best(A,eps);lb,lme,lnz,lrep=lattice_tile(A,eps,internal);cb,cme,cd=checker_tile(W,eps,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob)
                rows.append({'t0':t0,'c0':c0,'shape':list(A.shape),'sz3_bytes':sb,'sz3_orientation':so,'sz3_bps':8*sb/A.size,'lattice_bytes':lb,'lattice_gain':sb/lb,'lattice_bps':8*lb/A.size,'lattice_transition_nonzero':lnz,'lattice_rep':lrep,'checker_bytes':cb,'checker_gain':sb/cb,'checker_bps':8*cb/A.size,'checker_correction_nonzero':cd['correction_nonzero'],'spectral_bytes':pb,'spectral_gain':sb/pb,'spectral_bps':8*pb/A.size,'spectral_correction_nonzero':pd['correction_nonzero_fraction'],'maxerr':{'sz3':sme,'lattice':lme,'checker':cme,'spectral':pme}})
        S=sum(r['sz3_bytes'] for r in rows);agg=[]
        for k in ('lattice','checker','spectral'):
            b=sum(r[k+'_bytes'] for r in rows);samples=sum(np.prod(r['shape']) for r in rows);agg.append({'method':k,'bytes':b,'gain_vs_sz3':S/b,'bps':8*b/samples,'min_tile_gain':min(r[k+'_gain'] for r in rows),'median_tile_gain':float(np.median([r[k+'_gain'] for r in rows])),'max_tile_gain':max(r[k+'_gain'] for r in rows)})
        agg.sort(key=lambda x:x['bytes']);out={'file':os.path.basename(path),'dataset':name,'shape':list(shape),'dtype':dtype,'time_axis':ta,'das_channels':C-6,'das_std':std,'eps':eps,'tile_positions':{'time':tp,'channel':cp},'matched_sz3_bytes':S,'aggregate':agg,'rows':rows,'scope':'Nine deterministic full-resolution tiles spanning time and DAS channel axis. Global epsilon computed from all DAS samples in the full record, excluding first six published geophone traces. Same candidates/fairness as the full-record gate; diagnostic only.'}
        print(json.dumps(out,indent=2),flush=True);json.dump(out,open('cape_egs_das_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
