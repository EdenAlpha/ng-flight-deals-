import json,sys,math
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_address_aware_legal_search as q
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

P=32
HFAC=1.5
ROUNDS=2
VERSION=7


def fit_temporal(Q):
    Q=np.asarray(Q,np.float64);ts=np.arange(P,Q.shape[1],4,dtype=np.int32);cs=np.arange(Q.shape[0],dtype=np.int32);tt=np.repeat(ts,cs.size);cc=np.tile(cs,ts.size);y=Q[cc,tt]
    A=np.empty((y.size,P),np.float64)
    for j in range(P):A[:,j]=Q[cc,tt-(j+1)]
    M=np.column_stack([np.ones(A.shape[0]),A]);ridge=1e-5*np.eye(P+1);ridge[0,0]=0.0;beta=np.linalg.solve(M.T@M+ridge,M.T@y)
    co=np.rint(beta[1:]*x.g.SCALE).astype(np.int32);intercept=int(np.rint(beta[0]*x.g.SCALE));dts=np.arange(1,P+1,dtype=np.int16);dcs=np.zeros(P,np.int16)
    return dts,dcs,co,intercept


def build(X,eps):
    h=float(eps*HFAC);lo,hi=x.g.legal_q(X,eps,h);Q=x.g._initial(lo,hi,0);proj=0
    for _ in range(ROUNDS):
        dts,dcs,co,intercept=fit_temporal(Q);Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);proj+=int(ch)
    dts,dcs,co,intercept=fit_temporal(Q);Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);proj+=int(ch)
    lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(q.NBITS,np.float64);Q,D,cnt,ch,sc=q.causal_search(np.ascontiguousarray(Q),lo,hi,np.ascontiguousarray(D),dts,dcs,co,intercept,x.g.SCALE,q.MODES,lf,w,q.PASSES)
    Dr=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('temporal generator defect mismatch')
    return h,Q,D,dts,dcs,co,intercept,{'projection_changes':proj,'causal_changes':int(ch),'surrogate_bits':float(sc)}


def encode_model(co,intercept):
    out=bytearray()
    for v in co:x.put_svar(out,int(v))
    x.put_svar(out,int(intercept));return bytes(out)

def decode_model(buf,pos):
    co=[]
    for _ in range(P):v,pos=x.get_svar(buf,pos);co.append(v)
    inter,pos=x.get_svar(buf,pos);return np.asarray(co,np.int32),int(inter),pos


def strong_ar32(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);field,_=rc.compact_rich_defect(K);stream=bytes([8])+model+field;pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('AR strong parse')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR strong R')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError('AR hard')
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me,'model_rep':mname}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);ar32=strong_ar32(X,eps);h,Q,D,dts,dcs,co,intercept,search=build(X,eps);model=encode_model(co,intercept);field,detail=rc.compact_rich_defect(D);stream=bytes([VERSION])+model+field
    pos=1;co2,inter2,pos=decode_model(stream,pos);DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('NOVA temporal parse')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts,dcs,co2,inter2,x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('NOVA temporal Q')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('NOVA hard',me,eps))
    nova={'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me,'delta_vs_ar32':len(stream)-ar32['bytes'],'gain_vs_ar32':ar32['bytes']/len(stream),'gain_vs_sz3':szb/len(stream)}
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'h_factor':HFAC,'generator':'public temporal AR32-on-Q-lattice','sz3':{'bytes':int(szb),'orientation':ori},'strong_ar32':ar32,'nova_temporal':nova,'search':search,'coef_q12':[int(v) for v in co],'intercept_q12':int(intercept),'field_detail':detail,'scope':'Decoder-real hybrid test derived from the original shared-model/computation-for-communication idea. The NOVA side uses a public temporal 32-lag generator on the h=1.5epsilon legal reconstruction lattice rather than the prior OMP space-time tap grammar. Its Q12 coefficients/intercept are fully serialized; encoder computation alternates generator fitting, global hard-box legal projection, and causal-address-aware legal-state search. The final defect uses the same rich causal lossless coder given to the strong AR32 comparator. Both streams parse/replay exactly and satisfy the unchanged hard source error. This asks whether legal reconstruction freedom becomes more useful when paired with the incumbent temporal generator family.'};json.dump(out,open('imperial_legal_temporal_ar32_generator.json','w'),indent=2)
    print(json.dumps({'summary':{'nova':nova['bytes'],'strong_ar32':ar32['bytes'],'delta':nova['delta_vs_ar32'],'nova_model':nova['model_bytes'],'nova_field':nova['field_bytes'],'ar_model':ar32['model_bytes'],'ar_field':ar32['field_bytes'],'sz3':int(szb),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
