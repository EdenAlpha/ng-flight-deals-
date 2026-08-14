import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=2048
TB=1024
REGIONS=(('hard',512),('easy',2304))
a.NT=NT


def forward(K,name):
    K=np.asarray(K,np.int32)
    if name=='time_delta':
        T=K.copy();T[:,1:]=K[:,1:]-K[:,:-1];return T
    if name=='space_delta':
        T=K.copy();T[1:,:]=K[1:,:]-K[:-1,:];return T
    if name=='lorenzo2d':
        T=K.copy();T[1:,1:]=K[1:,1:]-K[1:,:-1]-K[:-1,1:]+K[:-1,:-1];return T
    if name=='space_lift':
        e=K[0::2,:].astype(np.int64);o=K[1::2,:].astype(np.int64)
        d=o-e;s=e+np.floor_divide(d,2)
        return np.concatenate((s,d),axis=0).astype(np.int32)
    if name=='time_lift':
        e=K[:,0::2].astype(np.int64);o=K[:,1::2].astype(np.int64)
        d=o-e;s=e+np.floor_divide(d,2)
        return np.concatenate((s,d),axis=1).astype(np.int32)
    if name=='lift2d':
        return forward(forward(K,'time_lift'),'space_lift')
    raise ValueError(name)


def inverse(T,name):
    T=np.asarray(T,np.int32)
    if name=='time_delta':return np.cumsum(T,axis=1,dtype=np.int32)
    if name=='space_delta':return np.cumsum(T,axis=0,dtype=np.int32)
    if name=='lorenzo2d':
        K=np.empty_like(T);K[0,:]=T[0,:];K[:,0]=T[:,0]
        for c in range(1,T.shape[0]):
            for t in range(1,T.shape[1]):
                K[c,t]=T[c,t]+K[c,t-1]+K[c-1,t]-K[c-1,t-1]
        return K
    if name=='space_lift':
        n=T.shape[0]//2;s=T[:n,:].astype(np.int64);d=T[n:,:].astype(np.int64)
        e=s-np.floor_divide(d,2);o=d+e
        K=np.empty_like(T);K[0::2,:]=e.astype(np.int32);K[1::2,:]=o.astype(np.int32);return K
    if name=='time_lift':
        n=T.shape[1]//2;s=T[:,:n].astype(np.int64);d=T[:,n:].astype(np.int64)
        e=s-np.floor_divide(d,2);o=d+e
        K=np.empty_like(T);K[:,0::2]=e.astype(np.int32);K[:,1::2]=o.astype(np.int32);return K
    if name=='lift2d':return inverse(inverse(T,'space_lift'),'time_lift')
    raise ValueError(name)


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            _,co=a.fits(X);R,K=a.run_ar(X,co)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',me,eps))
            bb,bbit,bnb,Kd=a.arithmetic(K)
            if not np.array_equal(Kd,K):raise RuntimeError((region,'baseline decode'))
            Rb=a.decode_source(Kd,co);bme=float(np.max(np.abs(X-Rb.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline replay hard',bme,eps))
            sz=0
            for t0 in range(0,NT,TB):n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)

            cands=[]
            for name in ('time_delta','space_delta','lorenzo2d','space_lift','time_lift','lift2d'):
                T=forward(K,name);Ki=inverse(T,name)
                if not np.array_equal(Ki,K):raise RuntimeError((region,name,'pre inverse'))
                n,nbit,nb,Td=a.arithmetic(T);n+=1
                K2=inverse(Td,name)
                if not np.array_equal(K2,K):raise RuntimeError((region,name,'decoded inverse'))
                R2=a.decode_source(K2,co);hme=float(np.max(np.abs(X-R2.astype(np.float64))))
                if hme>eps*(1+1e-12):raise RuntimeError((region,name,'hard',hme,eps))
                q={'transform':name,'bytes':int(n),'bps':8*n/X.size,
                   'gain_vs_direct_k':float(bb/n),'gain_vs_sz3':float(sz/n),
                   'zero_fraction':float(np.mean(T==0)),'field_std':float(np.std(T.astype(np.float64))),
                   'symbol_bits':int(nb),'arithmetic_bits':int(nbit),'maxerr':hme}
                cands.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            best=min(cands,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),
                 'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'zero_fraction':float(np.mean(K==0)),'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},'best':best,'candidates':cands}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        out={'rows':rows,'scope':'Exact post-quantization representation gate. The incumbent Huber AR32 step267 K field is left completely unchanged, so source fidelity is identical. Six reversible integer transforms of exact K are tested: temporal delta, spatial delta, 2-D Lorenzo, packed spatial Haar lifting, packed temporal Haar lifting, and separable 2-D lifting. Each transformed field is encoded/decoded by the same cold-start adaptive arithmetic engine, inverted bit-exactly back to K, replayed through the original AR32 decoder, and checked under the unchanged max-error contract. One selector byte is charged. Matched direct-K arithmetic and SZ3 rerun on hard/easy 128x2048. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_ar32_reversible_k_lifting.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
