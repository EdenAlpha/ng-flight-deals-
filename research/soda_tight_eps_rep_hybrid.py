import itertools,json,os,struct,sys
import numpy as np

# Audited run/event grammar + backend primitives.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())
# Preserve the PR #161 decoder before the generic sparse module imports its own
# historical decode_main symbol into this research globals() namespace.
decode_event_main=decode_main
# Audited exact dense/sparse/ternary integer-array codec, without its CLI.
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())

FROZEN_METHODS=(3,3,3,3,3,3,0,3,3,3)
FROZEN_ORDER=(0,1,2);FROZEN_CTXMODE=4;INTERNAL_SAFETY=1.0-1e-4
TMAG=b'TIGHTH01';TH='<8sddBBBBB3QQ';THS=struct.calcsize(TH)
# Conservative precommitted generic dictionary: physical/time-major variants,
# all exact representations, both strong Zstd levels.
GEN_PERMS=((0,1,2,3),(0,2,1,3),(3,1,2,0),(3,2,1,0),(1,2,0,3),(2,1,0,3))


def encode_event_fixed(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,FROZEN_ORDER,FROZEN_CTXMODE);frames=[]
    for i,(r,m) in enumerate(zip(rawframes,FROZEN_METHODS)):
        b=comp_one(r,m)
        if decomp_one(b,m)!=r:raise RuntimeError(('event backend roundtrip',i,m))
        frames.append(b)
    oc=int(FROZEN_ORDER[0]|(FROZEN_ORDER[1]<<2)|(FROZEN_ORDER[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,FROZEN_CTXMODE,*K.shape,*FROZEN_METHODS,*[len(x) for x in frames])
    return h+b''.join(frames),meta


def best_generic(Kc):
    rows=[]
    for level in (19,22):
        for perm in GEN_PERMS:
            for rep in (0,1,2):
                b=encode_array(Kc,perm,rep,level);R=decode_array(b)
                if not np.array_equal(R,Kc):raise RuntimeError(('generic decode',level,perm,rep))
                rows.append((len(b),level,perm,rep,b))
    rows.sort(key=lambda x:x[0]);w=rows[0]
    return w, [{'bytes':r[0],'level':r[1],'perm':list(r[2]),'rep':['raw','sparse','ternary'][r[3]]} for r in rows[:8]]


def encode_component_hybrid(K):
    blobs=[];modes=[];diag=[]
    for c in range(K.shape[0]):
        Kc=K[c:c+1]
        eb,em=encode_event_fixed(Kc);gw,gc=best_generic(Kc);gb=gw[4]
        if len(gb)<len(eb):mode=1;b=gb
        else:mode=0;b=eb
        blobs.append(b);modes.append(mode);diag.append({'component':c,'chosen':'generic' if mode else 'event','chosen_bytes':len(b),'event_bytes':len(eb),'generic_best':gc[0],'generic_candidates':gc,'K_nonzero_fraction':float(np.mean(Kc!=0))})
    return blobs,modes,diag


def decode_component(mode,blob):
    if mode==0:return decode_event_main(blob)
    if mode==1:return decode_array(blob)
    raise RuntimeError(('bad component mode',mode))


def decode_out_blob(blob,kind,td,Oshape):
    if kind==0:
        A=decode(blob).reshape(Oshape);return undelta(A,1) if td else A
    if kind==1:
        A=decode_out_sparse(blob);return undelta(A,1) if td else A
    raise RuntimeError(('bad outlier kind',kind))


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes)
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    bo=best_out(O);obb=bo[6];outkind=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0;RO=decode_out_blob(obb,outkind,td,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')

    # Existing whole-main frozen record, charged as the control.
    base_main,_=encode_event_fixed(K);baseK=decode_event_main(base_main)
    if not np.array_equal(baseK,K):raise RuntimeError('baseline exact K')
    base_container=TOPS+len(base_main)+len(obb)

    # New exact component representation hybrid.
    blobs,modes,cdiag=encode_component_hybrid(K);top=struct.pack(TH,TMAG,public_eps,internal_eps,outkind,td,*modes,*[len(b) for b in blobs],len(obb))+b''.join(blobs)+obb
    q=struct.unpack(TH,top[:THS]);magic,pe,ie,ok,td2,m0,m1,m2,l0,l1,l2,lo=q
    if magic!=TMAG:raise RuntimeError('tight hybrid header')
    p=THS;lens=(l0,l1,l2);RK=np.empty_like(K)
    for c,(m,L) in enumerate(zip((m0,m1,m2),lens)):
        b=top[p:p+L];p+=L;A=decode_component(m,b)
        if A.shape[0]!=1 or A.shape[1:]!=K.shape[1:]:raise RuntimeError(('component shape',c,A.shape,K.shape))
        RK[c]=A[0]
    rob=top[p:p+lo];p+=lo
    if p!=len(top):raise RuntimeError('tight hybrid length')
    ROut=decode_out_blob(rob,ok,td2,O.shape)
    if not np.array_equal(RK,K) or not np.array_equal(ROut,O):raise RuntimeError('tight hybrid exact integer decode')
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ie)
    Y[outids]=ROut.astype(np.float32)*np.float32(2*ie)
    me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps);hyb=len(top)
    out={'file':os.path.basename(path),'shape':list(X.shape),'std':std,'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'internal_safety':INTERNAL_SAFETY,'raw_bytes':raw,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'baseline_frozen':{'container_bytes':base_container,'ratio':raw/base_container,'gain_vs_sz3':szb/base_container},'component_hybrid':{'container_bytes':hyb,'ratio':raw/hyb,'gain_vs_sz3':szb/hyb,'component_modes':['generic' if m else 'event' for m in modes],'components':cdiag,'header_bytes':THS,'outlier_bytes':len(obb)},'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'maxerr':me,'valid':bool(me<=public_eps),'improvement_vs_frozen':base_container/hyb}
    if not out['valid']:raise RuntimeError(('hard error',me,public_eps,internal_eps))
    print(json.dumps({'frac':frac,'K_nonzero_fraction':out['K_nonzero_fraction'],'frozen_bytes':base_container,'hybrid_bytes':hyb,'improvement':out['improvement_vs_frozen'],'hybrid_gain_sz3':out['component_hybrid']['gain_vs_sz3'],'modes':out['component_hybrid']['component_modes'],'maxerr':me,'public_eps':public_eps},indent=2),flush=True)
    json.dump(out,open('soda_tight_eps_rep_hybrid.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
