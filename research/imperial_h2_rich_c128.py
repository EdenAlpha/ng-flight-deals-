import json,sys
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

C=128;T=1024;T0=14488;C0=512;P=32;STEP=267;K=x.K

def fit_general(Q,ntaps=K):
    Q=np.asarray(Q,np.float64);offs=x.g.candidate_offsets();maxdt=64;CC,TT=Q.shape
    ts=np.arange(maxdt,TT,4,dtype=np.int32);cs=np.arange(8,CC-8,dtype=np.int32);tt=np.repeat(ts,cs.size);cc=np.tile(cs,ts.size);y=Q[cc,tt]
    A=np.empty((y.size,len(offs)),np.float64)
    for j,(dt,dc) in enumerate(offs):A[:,j]=Q[cc+dc,tt-dt]
    ym=float(y.mean());y0=y-ym;means=A.mean(axis=0);scales=A.std(axis=0)+1e-8;An=(A-means)/scales
    selected=[];avail=np.ones(An.shape[1],bool);resid=y0.copy()
    for _ in range(ntaps):
        corr=np.abs(An.T@resid);corr[~avail]=-1;j=int(np.argmax(corr));selected.append(j);avail[j]=False
        B=An[:,selected];beta=np.linalg.lstsq(B,y0,rcond=1e-4)[0];resid=y0-B@beta
    B=A[:,selected];M=np.column_stack([np.ones(B.shape[0]),B]);ridge=1e-5*np.eye(M.shape[1]);ridge[0,0]=0;beta=np.linalg.solve(M.T@M+ridge,M.T@y)
    dts=np.asarray([offs[j][0] for j in selected],np.int16);dcs=np.asarray([offs[j][1] for j in selected],np.int16);co=np.rint(beta[1:]*x.g.SCALE).astype(np.int32);intercept=int(np.rint(beta[0]*x.g.SCALE))
    return dts,dcs,co,intercept

def nova(X,eps):
    h=2*eps;lo,hi=x.g.legal_q(X,eps,h)
    if np.any(lo!=hi):raise RuntimeError('h2 unique')
    Q=np.ascontiguousarray(lo.copy(),np.int32);dts,dcs,co,intercept=fit_general(Q);D=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE);model,_,_,_,_,_=x.compact_model(dts,dcs,co,intercept);field,detail=rc.compact_rich_defect(D);stream=bytes([15])+model+field
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32);DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('N field')
    Qd=np.empty_like(Q)
    for t in range(T):
        for c0 in range(C):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('N Q')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('N hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me},detail

def ar32(X,eps):
    co=car.ar.fit_shared(X[:,:256],P);R=np.zeros(X.shape,np.int32);Kf=np.zeros(X.shape,np.int32)
    for c0 in range(C):
        for t in range(T):
            pred=car.ar.predict_hist(R,c0,t,co,P,'shared');k=int(np.rint((float(X[c0,t])-pred)/STEP));R[c0,t]=pred+STEP*k;Kf[c0,t]=k
    model,mname=car.encode_model(co);field,detail=rc.compact_rich_defect(Kf);stream=bytes([16])+model+field;pos=1;cod,pos=car.decode_model(stream,pos,P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,Kf):raise RuntimeError('A field')
    Rd=np.zeros_like(R)
    for c0 in range(C):
        for t in range(T):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,P,'shared')+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('A R')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('A hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me},detail

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=x.m.szrun(X,eps);n,nd=nova(X,eps);a,ad=ar32(X,eps);n['delta_vs_ar32']=n['bytes']-a['bytes'];n['gain_vs_ar32']=a['bytes']/n['bytes'];n['gain_vs_sz3']=szb/n['bytes']
    out={'region':'hard','shape':[C,T],'global_std':std,'eps':eps,'h_factor':2.0,'sz3':{'bytes':int(szb),'orientation':ori},'nova_h2':n,'ar32':a,'nova_detail':nd,'ar_detail':ad,'scope':'Scale-transfer test of the exact h=2epsilon construction on a 128x1024 hard Imperial block. The learned 20-tap generator is refit over the wider block using the same public 112-offset grammar and fully charged compact model. NOVA defect and prefix-fit AR32 K use the identical rich causal coder. Both literal streams parse/replay exact internal fields and reconstructions and pass the unchanged hard error. No architecture tuning is performed on this wider block.'};json.dump(out,open('imperial_h2_rich_c128.json','w'),indent=2)
    print(json.dumps({'summary':{'NOVA':n['bytes'],'AR32':a['bytes'],'delta':n['delta_vs_ar32'],'gain_ar32':n['gain_vs_ar32'],'SZ3':int(szb),'NOVA_model':n['model_bytes'],'NOVA_field':n['field_bytes'],'AR_model':a['model_bytes'],'AR_field':a['field_bytes'],'maxerr':n['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
