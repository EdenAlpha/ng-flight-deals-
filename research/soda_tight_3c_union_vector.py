import json,os,struct,sys
import numpy as np

# Reuse the audited tight-fidelity lattice, geometry, outlier codec and current
# structural byte machinery.  This experiment changes only main-grid event
# timing/value factorization.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

UV_MAGIC=b'3CVEC001'
# magic,version,vector-kind,reorder,mag-dtype,outlier-kind,outlier-td,L,S,T,
# 6 timing method ids, 3 vector method ids, 9 frame lengths, outlier length
UV_HDR='<8sBBBBBB3I6B3B9QQ'
UV_HS=struct.calcsize(UV_HDR)
ORDER=(0,1,2);CTXMODE=4


def union_data(K):
    C,L,S,T=K.shape
    if C!=3:raise RuntimeError(('3C required',K.shape))
    union=np.any(K!=0,axis=0);U=union.astype(np.int32)[None,...]
    rows=[]
    for l in range(L):
        for s in range(S):
            pos=np.flatnonzero(union[l,s])
            if pos.size:rows.append(K[:,l,s,pos].T.copy())
    V=np.concatenate(rows,axis=0) if rows else np.empty((0,3),np.int32)
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(U,ORDER)
    if vals.size!=V.shape[0] or (vals.size and not np.all(vals==1)):raise RuntimeError(('union order mismatch',vals.size,V.shape))
    return U,V,phase,diag


def compress_raw_frames(raws):
    frames=[];methods=[];choices=[]
    for i,r in enumerate(raws):
        best,allrows=best_comp(r);n,m,b=best;frames.append(b);methods.append(m);choices.append({'frame':i,'raw_bytes':len(r),'method':METHOD_NAMES[m],'bytes':n,'all':allrows})
    return frames,methods,choices


def timing_frames(U):
    sh,dc,raw,meta=prepare_raw_frames(U,ORDER,CTXMODE)
    frames,methods,choices=compress_raw_frames(raw[:6])
    return frames,methods,choices,meta


def event_perm(phase,reorder):
    if not reorder:return np.arange(len(phase),dtype=np.int64)
    return np.argsort(np.asarray(phase),kind='stable')


def encode_vectors(V,phase,kind,reorder):
    p=event_perm(phase,reorder);W=np.asarray(V,np.int32)[p]
    raws=[];dc=1;diag={'kind':kind,'reorder':'runphase' if reorder else 'trace','events':int(W.shape[0])}
    if kind==0:
        # Raw exact signed 3-vector stream; zeros make component identity implicit.
        dc=dtype_code(W.ravel());raws=[W.astype(DT[dc],copy=False).tobytes(),b'',b'']
    elif kind==1:
        # Ternary sign vector: each component symbol 0/positive/negative.  Mask
        # and sign are therefore one base-3 joint symbol (0..26).  Exceptional
        # support and magnitudes are only over already-active components.
        tri=np.zeros(W.shape,np.uint8);tri[W>0]=1;tri[W<0]=2
        sym=(tri[:,0]+3*tri[:,1]+9*tri[:,2]).astype(np.uint8)
        active=W!=0;av=np.abs(W[active]);exc=av>1;mag=(av[exc]-2).astype(np.int32);dc=dtype_code(mag)
        raws=[sym.tobytes(),np.packbits(exc,bitorder='little').tobytes(),mag.astype(DT[dc],copy=False).tobytes()]
        diag.update({'active_values':int(active.sum()),'exceptions':int(exc.sum()),'exception_fraction':float(exc.mean()) if exc.size else 0.0})
    elif kind==2:
        # Per-component 2-bit alphabet: 0,+1,-1,exception. Exception support is
        # folded into the 6-bit joint vector symbol; only exception signs and
        # exact magnitudes remain as side planes.
        code=np.zeros(W.shape,np.uint8);code[W==1]=1;code[W==-1]=2;exc=np.abs(W)>1;code[exc]=3
        sym=(code[:,0]|(code[:,1]<<2)|(code[:,2]<<4)).astype(np.uint8)
        ev=W[exc];sgn=ev<0;mag=(np.abs(ev)-2).astype(np.int32);dc=dtype_code(mag)
        raws=[sym.tobytes(),np.packbits(sgn,bitorder='little').tobytes(),mag.astype(DT[dc],copy=False).tobytes()]
        diag.update({'exceptions':int(exc.sum()),'exception_fraction_of_components':float(exc.mean()) if exc.size else 0.0})
    else:raise ValueError(kind)
    frames,methods,choices=compress_raw_frames(raws);diag['backend_choices']=choices
    return frames,methods,dc,diag


def decode_vectors(raws,n,phase,kind,reorder,dc):
    if kind==0:
        W=np.frombuffer(raws[0],dtype=DT[dc],count=n*3).astype(np.int32).reshape(n,3)
    elif kind==1:
        sym=np.frombuffer(raws[0],np.uint8,count=n);tri=np.empty((n,3),np.uint8);tri[:,0]=sym%3;tri[:,1]=(sym//3)%3;tri[:,2]=(sym//9)%3
        W=np.zeros((n,3),np.int32);W[tri==1]=1;W[tri==2]=-1;active=tri!=0;na=int(active.sum());exc=np.unpackbits(np.frombuffer(raws[1],np.uint8),bitorder='little',count=na).astype(bool);mag=np.frombuffer(raws[2],dtype=DT[dc],count=int(exc.sum())).astype(np.int32)
        vals=np.ones(na,np.int32);vals[exc]=mag+2;sign=(tri[active]==2);vals[sign]*=-1;W[active]=vals
    elif kind==2:
        sym=np.frombuffer(raws[0],np.uint8,count=n);code=np.empty((n,3),np.uint8);code[:,0]=sym&3;code[:,1]=(sym>>2)&3;code[:,2]=(sym>>4)&3
        W=np.zeros((n,3),np.int32);W[code==1]=1;W[code==2]=-1;exc=code==3;ne=int(exc.sum());sgn=np.unpackbits(np.frombuffer(raws[1],np.uint8),bitorder='little',count=ne).astype(bool);mag=np.frombuffer(raws[2],dtype=DT[dc],count=ne).astype(np.int32);v=mag+2;v[sgn]*=-1;W[exc]=v
    else:raise RuntimeError(('vector kind',kind))
    if reorder:
        p=event_perm(phase,True);out=np.empty_like(W);out[p]=W;W=out
    return W


def decode_union_timing(raw,L,S,T):
    psh=(1,L,S,T);ntr=L*S
    rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,ORDER,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,ORDER,psh);ictx=inter_context(rc,runlens,rcomp,CTXMODE);ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ictx).astype(np.int32);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2
    rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows)
    return rows,phase


def fill_K(rows,V,L,S,T):
    K=np.zeros((3,L,S,T),np.int32);k=0;i=0
    for l in range(L):
        for s in range(S):
            pos=rows[i];i+=1;c=pos.size
            if c:K[:,l,s,pos]=V[k:k+c].T;k+=c
    if k!=V.shape[0]:raise RuntimeError(('vector fill accounting',k,V.shape[0]))
    return K


def outlier_decode_blob(blob,kind,td,Oshape):
    if kind==0:
        A=decode(blob).reshape(Oshape);return undelta(A,1) if td else A
    A=decode_out_sparse(blob);return undelta(A,1) if td else A


def encode_union_candidate(K,O,kind,reorder):
    U,V,phase,udiag=union_data(K);tf,tm,tc,tmeta=timing_frames(U);vf,vm,dc,vdiag=encode_vectors(V,phase,kind,reorder);bo=best_out(O);obb=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0;L,S,T=K.shape[1:]
    lens=[len(x) for x in tf+vf];h=struct.pack(UV_HDR,UV_MAGIC,1,kind,int(reorder),dc,ok,td,L,S,T,*tm,*vm,*lens,len(obb));blob=h+b''.join(tf)+b''.join(vf)+obb
    parts={'header_bytes':UV_HS,'timing_bytes':sum(len(x) for x in tf),'vector_bytes':sum(len(x) for x in vf),'outlier_bytes':len(obb),'timing_choices':tc,'vector_diag':vdiag,'union_diag':udiag,'timing_meta':tmeta,'outlier_kind':bo[1],'outlier_tdiff':bool(bo[2])}
    return blob,parts


def decode_union_candidate(blob,Oshape):
    q=struct.unpack(UV_HDR,blob[:UV_HS]);magic,ver,kind,reorder,dc,ok,td,L,S,T,*rest=q
    if magic!=UV_MAGIC or ver!=1:raise RuntimeError('3C vector header')
    tm=rest[:6];vm=rest[6:9];lens=rest[9:18];lo=rest[18];p=UV_HS;frames=[]
    for n in lens:frames.append(blob[p:p+n]);p+=n
    obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('3C vector length')
    traw=[decomp_one(frames[i],tm[i]) for i in range(6)];vraw=[decomp_one(frames[6+i],vm[i]) for i in range(3)];rows,phase=decode_union_timing(traw,L,S,T);n=int(sum(r.size for r in rows));V=decode_vectors(vraw,n,phase,kind,bool(reorder),dc);K=fill_K(rows,V,L,S,T);O=outlier_decode_blob(obb,ok,td,Oshape)
    return K,O


def incumbent_container(K,O):
    cache=structural_sequences(K);rows=[]
    for r2 in (0,1):
        for r9 in (0,1):
            mb,parts=encode_main_candidate(K,r2,r9,cache);R=decode_main_candidate(mb)
            if not np.array_equal(R,K):raise RuntimeError('incumbent K')
            rows.append((len(mb),mb,parts,r2,r9))
    rows.sort(key=lambda r:r[0]);bo=best_out(O);return TOP_HS+rows[0][0]+int(bo[0]),rows[0],bo


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);inc,incmain,incbo=incumbent_container(K,O);rows=[]
    for kind in (0,1,2):
        for reorder in (False,True):
            blob,parts=encode_union_candidate(K,O,kind,reorder);RK,RO=decode_union_candidate(blob,O.shape)
            if not np.array_equal(RK,K) or not np.array_equal(RO,O):raise RuntimeError(('3C exact integer decode',kind,reorder))
            RG=undelta(RK,3);Y=np.empty_like(X)
            for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
            Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)))
            if me>public_eps*(1+3e-6):raise RuntimeError(('3C hard error',kind,reorder,me,public_eps))
            rows.append({'kind':kind,'kind_name':['raw-vector','ternary-sign-vector','small4-vector'][kind],'reorder':'runphase' if reorder else 'trace','container_bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':True,'parts':parts})
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];szb,sze=sz3_bytes(X,public_eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'incumbent':{'container_bytes':inc,'ratio':raw/inc,'gain_vs_sz3':szb/inc,'main_bytes':incmain[0],'main_parts':incmain[2]},'best_union_vector':best,'all_union_vector':rows,'improvement_vs_incumbent':inc/best['container_bytes'],'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':szb/best['container_bytes']}
    print(json.dumps({'frac':frac,'incumbent_bytes':inc,'best_kind':best['kind_name'],'reorder':best['reorder'],'best_bytes':best['container_bytes'],'improvement':out['improvement_vs_incumbent'],'gain_sz3':out['gain_vs_direct_sz3'],'timing_bytes':best['parts']['timing_bytes'],'vector_bytes':best['parts']['vector_bytes']},indent=2),flush=True);json.dump(out,open('soda_tight_3c_union_vector.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
