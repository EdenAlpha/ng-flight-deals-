import json,sys,math
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_h2_rich_causal_headtohead as h2

KS=(8,12,16,20,24,28,32)
OFFS=x.g.candidate_offsets();N=len(OFFS)
HFAC=2.0


def encode_model_var(dts,dcs,co,intercept,k):
    lut={tuple(v):i for i,v in enumerate(OFFS)};ids=[lut[(int(dt),int(dc))] for dt,dc in zip(dts,dcs)]
    if len(ids)!=k or len(set(ids))!=k:raise RuntimeError(('tap ids',k,len(ids),len(set(ids))))
    order=np.argsort(np.asarray(ids));sid=[ids[int(i)] for i in order];sco=[int(co[int(i)]) for i in order]
    rb=(math.comb(N,k).bit_length()+7)//8;rank=x.rank_combination(sid,N,k);out=bytearray(rank.to_bytes(rb,'little'))
    for v in sco:x.put_svar(out,v)
    x.put_svar(out,int(intercept))
    return bytes(out),rb,sid,sco


def decode_model_var(buf,pos,k):
    rb=(math.comb(N,k).bit_length()+7)//8;rank=int.from_bytes(buf[pos:pos+rb],'little');pos+=rb;ids=x.unrank_combination(rank,N,k);co=[]
    for _ in range(k):v,pos=x.get_svar(buf,pos);co.append(v)
    inter,pos=x.get_svar(buf,pos);dts=np.asarray([OFFS[i][0] for i in ids],np.int16);dcs=np.asarray([OFFS[i][1] for i in ids],np.int16)
    return dts,dcs,np.asarray(co,np.int32),int(inter),pos


def run_k(X,eps,cid,k):
    h=2.0*eps;lo,hi=x.g.legal_q(X,eps,h)
    if np.any(lo!=hi):raise RuntimeError('h2 unique failed')
    Q=np.ascontiguousarray(lo.copy(),np.int32);dts,dcs,co,intercept=x.g.fit_model(Q,ntaps=k);D=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
    model,rank_bytes,ids,sco=encode_model_var(dts,dcs,co,intercept,k);field,detail=rc.compact_rich_defect(D);stream=bytes([cid])+model+field
    pos=0;cid2=int(stream[pos]);pos+=1
    if cid2!=cid:raise RuntimeError('selector')
    k2=KS[cid2];ddt,ddc,dco,dinter,pos=decode_model_var(stream,pos,k2);DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError(('field replay',k))
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,ddt,ddc,dco,dinter,x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',k))
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',k,me,eps))
    return {'selector':cid,'ntaps':k,'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'rank_bytes':rank_bytes,'maxerr':me,'tap_ids':ids,'coef_q12':sco,'intercept_q12':int(intercept),'field_detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);ar32,_=h2.encode_ar32(X,eps);rows=[]
    for cid,k in enumerate(KS):
        r=run_k(X,eps,cid,k);r['delta_vs_rich_ar32']=r['bytes']-ar32['bytes'];r['gain_vs_rich_ar32']=ar32['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];rows.append(r);print(json.dumps({q:v for q,v in r.items() if q not in ('tap_ids','coef_q12','field_detail')},flush=True))
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'h_factor':HFAC,'candidate_ntaps':list(KS),'rich_ar32':ar32,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Decoder-real generator-complexity search on the deterministic h=2epsilon lattice. The public candidate tap counts are 8/12/16/20/24/28/32 over the same 112-offset grammar. For every candidate, the encoder fits the sparse generator, transmits a real one-byte tap-count selector, exact combinatorial tap-set rank, signed-varint Q12 coefficients/intercept, and the same rich causal defect coder used by AR32. Decoder parses the chosen model/field, reproduces exact Q and source reconstruction, and hard-error verifies. All final bytes are materialized; no uncharged model selection.'}
    json.dump(out,open('imperial_h2_generator_complexity.json','w'),indent=2);print(json.dumps({'summary':{'best_ntaps':best['ntaps'],'NOVA':best['bytes'],'rich_AR32':ar32['bytes'],'delta':best['delta_vs_rich_ar32'],'gain_ar32':best['gain_vs_rich_ar32'],'SZ3':int(szb),'model':best['model_bytes'],'field':best['field_bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
