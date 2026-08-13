import json,sys,math
from collections import Counter
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;DICT_END=4096;END=8192;STEP=267
LENS=(4,8);SIZES=(64,256,1024);SAFETY=1-1e-9
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def fit_model(X):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);return mb,cd

def pred(state,co):
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*state[-1-j]
    return int(np.rint(v))

def legal_ks(x,p,eps):
    b=eps*SAFETY;lo=int(math.ceil((float(x)-b-p)/STEP-1e-12));hi=int(math.floor((float(x)+b-p)/STEP+1e-12));return range(lo,hi+1)

def greedy_full(X,co,eps):
    R=np.zeros(X.shape,np.int64);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        st=np.zeros(P,np.int64)
        for t in range(X.shape[1]):
            p=pred(st,co) if t>=P else 0;k=int(np.rint((float(X[c,t])-p)/STEP));rr=p+STEP*k
            if abs(float(X[c,t])-rr)>eps*(1+1e-10):raise RuntimeError(('greedy hard',c,t))
            R[c,t]=rr;K[c,t]=k;st[:-1]=st[1:];st[-1]=rr
    return R,K

def shapes_from_prefix(K,L,N):
    cnt=Counter()
    for c in range(K.shape[0]):
        a=K[c,TRAIN:DICT_END]
        for t in range(0,len(a)-L+1):
            z=a[t:t+L].astype(np.int64);sh=tuple((z-z[0]).tolist());cnt[sh]+=1
    top=cnt.most_common(N);shapes=[np.asarray(k,np.int32) for k,v in top];freq=np.asarray([v for k,v in top],np.int64)
    return shapes,freq,int(sum(cnt.values())),int(len(cnt))

def make_trie(shapes):
    root={}
    for sid,s in enumerate(shapes):
        node=root
        for j in range(1,len(s)):
            d=int(s[j]);node=node.setdefault(d,{})
        node['_id']=sid
    return root

def search_phrase(x,st,co,eps,L,trie,shape_cost):
    best=None
    p0=pred(st,co);ks0=list(legal_ks(x[0],p0,eps))
    for a in ks0:
        rr=p0+STEP*a
        st1=st.copy();st1[:-1]=st1[1:];st1[-1]=rr
        stack=[(1,trie,st1,[a])]
        while stack:
            j,node,state,ks=stack.pop()
            if j==L:
                sid=node.get('_id')
                if sid is not None:
                    cost=float(shape_cost[sid])+math.log2(2+abs(int(a)))
                    if best is None or cost<best[0]:best=(cost,sid,int(a),state.copy(),np.asarray(ks,np.int32))
                continue
            pp=pred(state,co)
            for k in legal_ks(x[j],pp,eps):
                d=int(k-a);child=node.get(d)
                if child is None:continue
                rr=pp+STEP*int(k);ns=state.copy();ns[:-1]=ns[1:];ns[-1]=rr
                stack.append((j+1,child,ns,ks+[int(k)]))
    return best

def kframe(vals):
    vals=np.asarray(vals,np.int32)
    if vals.size==0:return 0,'empty',vals.copy()
    fr=m.encode_k(vals.reshape(1,-1));return int(fr[0])+20,fr[1],np.asarray(fr[2],np.int32).ravel()

def idframe(ids,N):
    ids=np.asarray(ids,np.int32);dt=np.uint8 if N<=256 else np.dtype('<u2');a=ids.astype(dt);zb=ZC.compress(a.tobytes());back=np.frombuffer(ZD.decompress(zb),dt,count=a.size).astype(np.int32)
    if not np.array_equal(back,ids):raise RuntimeError('id rt')
    return len(zb)+28,back,np.dtype(dt).str

def maskframe(mask):
    a=np.asarray(mask,np.uint8);zb=ZC.compress(np.packbits(a,bitorder='little').tobytes());back=np.unpackbits(np.frombuffer(ZD.decompress(zb),np.uint8),bitorder='little')[:a.size].astype(np.uint8)
    if not np.array_equal(back,a):raise RuntimeError('mask rt')
    return len(zb)+24,back

def encode_target(X,Rprefix,co,eps,L,shapes,freq):
    N=len(shapes);trie=make_trie(shapes);tot=freq.sum();shape_cost=-np.log2((freq+.5)/(tot+.5*N))
    modes=[];ids=[];anchors=[];esc=[];Kused=[];Rout=np.empty((C,END-DICT_END),np.int64);match_by_c=[]
    for c in range(C):
        st=Rprefix[c,DICT_END-P:DICT_END].astype(np.int64).copy();u=0;matches=0
        while u<END-DICT_END:
            n=min(L,END-DICT_END-u);xx=X[c,DICT_END+u:DICT_END+u+n]
            hit=search_phrase(xx,st,co,eps,L,trie,shape_cost) if n==L else None
            if hit is not None:
                _,sid,a,nst,ks=hit;modes.append(1);ids.append(sid);anchors.append(a);Kused.extend(ks.tolist())
                # replay for output (nst only has last P state, while we need all samples)
                for j,k in enumerate(ks):
                    pp=pred(st,co);rr=pp+STEP*int(k);Rout[c,u+j]=rr;st[:-1]=st[1:];st[-1]=rr
                matches+=1;u+=L
            else:
                modes.append(0);ids.append(0);anchors.append(0);kk=[]
                for j in range(n):
                    pp=pred(st,co);k=int(np.rint((float(xx[j])-pp)/STEP));rr=pp+STEP*k
                    if abs(float(xx[j])-rr)>eps*(1+1e-10):raise RuntimeError(('escape hard',c,u+j))
                    kk.append(k);esc.append(k);Kused.append(k);Rout[c,u+j]=rr;st[:-1]=st[1:];st[-1]=rr
                u+=n
        match_by_c.append(matches/max(1,math.ceil((END-DICT_END)/L)))
    modes=np.asarray(modes,np.uint8);ids=np.asarray(ids,np.int32);anchors=np.asarray(anchors,np.int32)
    mb,md=maskframe(modes);hit=modes.astype(bool);ib,idd,idt=idframe(ids[hit],N) if np.any(hit) else (0,np.empty(0,np.int32),'none');ab,arep,ad=kframe(anchors[hit]);eb,erep,ed=kframe(np.asarray(esc,np.int32));total=mb+ib+ab+eb+64
    # decode/reconstruct from streams
    idp=ap=ep=0;Rd=np.empty_like(Rout)
    for c in range(C):
        st=Rprefix[c,DICT_END-P:DICT_END].astype(np.int64).copy();u=0
        while u<END-DICT_END:
            n=min(L,END-DICT_END-u);mode=bool(md[(c*math.ceil((END-DICT_END)/L))+(u//L)])
            if mode and n==L:
                sid=int(idd[idp]);a=int(ad[ap]);idp+=1;ap+=1;ks=a+shapes[sid].astype(np.int32)
            else:
                ks=ed[ep:ep+n];ep+=n
            for j,k in enumerate(ks):
                pp=pred(st,co);rr=pp+STEP*int(k);Rd[c,u+j]=rr;st[:-1]=st[1:];st[-1]=rr
            u+=n
    if idp!=len(idd) or ap!=len(ad) or ep!=len(ed):raise RuntimeError(('stream accounting',idp,ap,ep,len(idd),len(ad),len(ed)))
    if not np.array_equal(Rd,Rout):raise RuntimeError('decode state mismatch')
    me=float(np.max(np.abs(X[:,DICT_END:END]-Rd)))
    if me>eps*(1+1e-10):raise RuntimeError(('final hard',me,eps))
    return {'bytes':total,'bps':8*total/Rd.size,'mode_bytes':mb,'id_bytes':ib,'id_dtype':idt,'anchor_bytes':ab,'anchor_rep':arep,'escape_bytes':eb,'escape_rep':erep,'phrase_fraction':float(np.mean(modes)),'median_channel_phrase_fraction':float(np.median(match_by_c)),'maxerr':me,'unique_target_ids':int(np.unique(ids[hit]).size) if np.any(hit) else 0}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    model_bytes,co=fit_model(X);Rg,Kg=greedy_full(X,co,eps)
    baseK=Kg[:,DICT_END:END];bf=m.encode_k(baseK);base_bytes=model_bytes+int(bf[0])+20;target=X[:,DICT_END:END];sb,_=m.szrun(target,eps)
    rows=[]
    for L in LENS:
        for N in SIZES:
            shapes,freq,total_shapes,unique_shapes=shapes_from_prefix(Kg,L,N);res=encode_target(X,Rg,co,eps,L,shapes,freq);res.update({'L':L,'dictionary_size':N,'prefix_shape_windows':total_shapes,'prefix_unique_shapes':unique_shapes,'dictionary_top1_fraction':float(freq[0]/freq.sum()),'dictionary_coverage_mass':float(freq.sum()/total_shapes),'model_bytes':model_bytes,'total_with_model':res['bytes']+model_bytes,'bps_with_model':8*(res['bytes']+model_bytes)/target.size,'baseline_bytes':base_bytes,'baseline_bps':8*base_bytes/target.size,'gain_vs_greedy_ar32':base_bytes/(res['bytes']+model_bytes),'sz3_bytes':int(sb),'gain_vs_sz3':sb/(res['bytes']+model_bytes)})
            rows.append(res);print(json.dumps(res,indent=2),flush=True)
    rows.sort(key=lambda z:z['total_with_model']);out={'global_std':std,'eps':eps,'step':STEP,'ar_order':P,'training_samples':TRAIN,'dictionary_interval':[TRAIN,DICT_END],'target_interval':[DICT_END,END],'channels':[C0,C0+C-1],'model_bytes':model_bytes,'baseline':{'bytes':base_bytes,'bps':8*base_bytes/target.size,'sz3_bytes':int(sb),'sz3_bps':8*sb/target.size,'gain_vs_sz3':sb/base_bytes},'best':rows[0],'rows':rows,'scope':'State-conditioned legal innovation-phrase codec screen. One shared AR32 model is fitted/serialized from t<1024. The already-decoded greedy step267 prefix t=1024..4095 defines a decoder-known dictionary of frequent relative K shapes: shape=(0,K1-K0,...). For the held-out target t=4096..8191, blocks of L=4/8 are processed sequentially in the actual evolving AR decoder state. A trie enumerates only dictionary shapes whose anchored K sequence keeps every reconstructed target sample inside the unchanged +/-epsilon interval. Hits transmit mode + shape ID + one anchor K; misses transmit exact greedy escape K values. Dictionary contents/counts are derived from already-decoded prefix and cost zero target metadata; all target mode/ID/anchor/escape streams are actually Zstd/encode_k serialized and decoded, then the complete AR trajectory is regenerated and hard-error verified. Model bytes are charged once; matched SZ3 and greedy persistent AR32 are rerun on the identical 128x4096 target. This is a continuation/held-out target screen, not a whole-array claim. No AI.'}
    print(json.dumps({'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_state_conditioned_phrase_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
