import json,sys,math
import h5py
import numpy as np

T=1024
ANCHORS=384
MAX_OFF=1024
STARTS=(0,14488,28976)

def norm_channels(A):
    X=A.astype(np.float64).T
    X-=X.mean(axis=1,keepdims=True)
    n=np.sqrt(np.sum(X*X,axis=1,keepdims=True))
    n[n==0]=1.0
    return X/n

def pair_stats(Z,anchors,eps):
    C=Z.shape[0]
    ZA=Z[anchors]
    M=ZA@Z.T
    for i,a in enumerate(anchors):M[i,a]=0.0
    j=np.argmax(np.abs(M),axis=1);v=M[np.arange(len(anchors)),j]
    best=[{'anchor':int(a),'partner':int(b),'offset':int(b-a),'abs_offset':int(abs(b-a)),'corr':float(c)} for a,b,c in zip(anchors,j,v)]
    rows=[]
    for off in range(1,MAX_OFF+1):
        ok=anchors+off<C
        if not np.any(ok):break
        aa=anchors[ok];vals=M[np.where(ok)[0],aa+off]
        rows.append({'offset':off,'mean_abs_corr':float(np.mean(np.abs(vals))),'median_abs_corr':float(np.median(np.abs(vals))),'mean_corr':float(np.mean(vals)),'n':int(vals.size)})
    return best,rows

def reorder_score(Z,s):
    C=Z.shape[0];vals=[]
    for r in range(s):
        idx=np.arange(r,C,s,dtype=np.int32)
        if idx.size<2:continue
        if idx.size>512:
            take=np.linspace(0,idx.size-2,512,dtype=np.int32);a=idx[take];b=idx[take+1]
        else:a=idx[:-1];b=idx[1:]
        vals.append(np.sum(Z[a]*Z[b],axis=1))
    if not vals:return None
    v=np.concatenate(vals)
    return {'stride':int(s),'mean_abs_corr':float(np.mean(np.abs(v))),'median_abs_corr':float(np.median(np.abs(v))),'mean_corr':float(np.mean(v)),'pairs':int(v.size)}

def overlap_score(A,off,eps):
    C=A.shape[1];p=min(512,C-off)
    if p<=0:return None
    idx=np.linspace(0,C-off-1,p,dtype=np.int32);ti=np.linspace(0,A.shape[0]-1,min(256,A.shape[0]),dtype=np.int32)
    D=np.abs(A[np.ix_(ti,idx)].astype(np.float64)-A[np.ix_(ti,idx+off)].astype(np.float64))
    return float(np.mean(D<=2*eps))

def main(path):
    with h5py.File(path,'r') as f:
        data=f['Acoustic'];s=ss=0.0;n=0
        for t0 in range(0,data.shape[0],2048):
            x=np.asarray(data[t0:min(data.shape[0],t0+2048)],dtype=np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
        mu=s/n;std=math.sqrt(max(0.0,ss/n-mu*mu));eps=.1*std;C=data.shape[1]
        anchors=np.linspace(0,C-1,ANCHORS,dtype=np.int32);all_best=[];off_acc={};perm_acc={};overlap_acc={}
        divisors=[x for x in range(1,C+1) if C%x==0 and x<=1024]
        candidate_strides=sorted(set(divisors+[27,54,108,216,256,288,384,432,512,576,768,864,1024]));windows=[]
        for st in STARTS:
            A=np.asarray(data[st:st+T],dtype=np.float32);Z=norm_channels(A);best,rows=pair_stats(Z,anchors,eps);all_best.extend(best)
            for r in rows:off_acc.setdefault(r['offset'],[]).append(r)
            for q in candidate_strides:
                if q<C:
                    r=reorder_score(Z,q)
                    if r:perm_acc.setdefault(q,[]).append(r)
            windows.append({'start':st,'best_partner_median_abs_corr':float(np.median([abs(x['corr']) for x in best])),'best_partner_mean_abs_corr':float(np.mean([abs(x['corr']) for x in best]))})
        offsets=[]
        for off,rr in off_acc.items():
            offsets.append({'offset':off,'mean_abs_corr':float(np.mean([x['mean_abs_corr'] for x in rr])),'median_abs_corr':float(np.mean([x['median_abs_corr'] for x in rr])),'mean_corr':float(np.mean([x['mean_corr'] for x in rr]))})
        offsets.sort(key=lambda x:x['mean_abs_corr'],reverse=True)
        test_off=sorted(set([r['offset'] for r in offsets[:40]]+[1,2,3,4,6,8,9,12,16,18,24,27,32,36,48,54,64,72,96,108,128,144,192,216,256,288,384,432,512,576,768,864,1024]))
        for st in STARTS:
            A=np.asarray(data[st:st+T],dtype=np.float32)
            for q in test_off:
                if q<C:overlap_acc.setdefault(q,[]).append(overlap_score(A,q,eps))
        overlap=[{'offset':q,'legal_interval_overlap':float(np.mean(v))} for q,v in overlap_acc.items()];overlap.sort(key=lambda x:x['legal_interval_overlap'],reverse=True)
        perms=[]
        for q,rr in perm_acc.items():perms.append({'stride':q,'mean_abs_corr':float(np.mean([x['mean_abs_corr'] for x in rr])),'median_abs_corr':float(np.mean([x['median_abs_corr'] for x in rr])),'mean_corr':float(np.mean([x['mean_corr'] for x in rr]))})
        perms.sort(key=lambda x:x['mean_abs_corr'],reverse=True)
        hist={}
        for r in all_best:hist[r['abs_offset']]=hist.get(r['abs_offset'],0)+1
        histrows=sorted(({'abs_offset':int(k),'count':int(v),'fraction':v/len(all_best)} for k,v in hist.items()),key=lambda x:x['count'],reverse=True)
        out={'shape':list(data.shape),'dtype':str(data.dtype),'global_std':std,'eps':eps,'windows':windows,'nearest_partner_abs_corr_median':float(np.median([abs(x['corr']) for x in all_best])),'nearest_partner_abs_corr_mean':float(np.mean([abs(x['corr']) for x in all_best])),'top_nearest_partner_offsets':histrows[:40],'top_fixed_offsets':offsets[:50],'top_legal_interval_overlap_offsets':overlap[:50],'top_interleaving_stride_scores':perms[:40],'interpretation':'If a hidden acquisition permutation exists, best-partner offsets and/or an interleaving stride should concentrate sharply and greatly exceed stored-adjacent offset 1. Diagnostic only; no compression claim.'}
        print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_hidden_channel_topology.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
