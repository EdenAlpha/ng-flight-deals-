import json,os,struct,sys
import numpy as np

# Reuse PR #176's audited modern run/Rice grammar, geometry, exact backend menu,
# outlier dictionary and full byte decoders without running its CLI.
src=open('research/soda_tight_rice_frames.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

NPH=16
PHMAG=b'TPHRICE1'
PHHDR='<8sdBBBB4Q'
PHHS=struct.calcsize(PHHDR)


def choose_trace_phase(x,step):
    # Same-step legal lattice-origin search frozen from PR #120.  The lattice
    # spacing remains exactly 2*internal_eps, so every shifted nearest lattice
    # still has worst-case error <= internal_eps.  We search only the fixed 16
    # origins and serialize the chosen 4-bit phase index.
    xd=x.astype(np.float64,copy=False);best=None
    for k in range(NPH):
        phi=step*(k/NPH);q=np.rint((xd-phi)/step).astype(np.int32)
        d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1]
        nz=int(np.count_nonzero(d));big=int(np.count_nonzero(np.abs(d)>1));mag=int(np.abs(d.astype(np.int64)).sum())
        score=(nz,big,mag,k)
        if best is None or score<best[0]:best=(score,k,q)
    return int(best[1]),best[2]


def phase_quantize(X,tm,outids,shape,step):
    G=np.zeros(shape,np.int32);P=np.zeros(shape[:-1],np.uint8);before=after=0;big0=big1=0
    for tid,c,l,s in tm:
        x=X[tid];q0=np.rint(x.astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];before+=int(np.count_nonzero(d0));big0+=int(np.count_nonzero(np.abs(d0)>1))
        k,q=choose_trace_phase(x,step);P[c,l,s]=k;G[c,l,s]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];after+=int(np.count_nonzero(d));big1+=int(np.count_nonzero(np.abs(d)>1))
    O=np.empty((len(outids),X.shape[1]),np.int32);OP=np.zeros(len(outids),np.uint8);obefore=oafter=0
    for j,tid in enumerate(outids.tolist()):
        x=X[tid];q0=np.rint(x.astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];obefore+=int(np.count_nonzero(d0))
        k,q=choose_trace_phase(x,step);OP[j]=k;O[j]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];oafter+=int(np.count_nonzero(d))
    return G,P,O,OP,{'main_events_before':before,'main_events_after':after,'main_event_reduction':float(1-after/max(1,before)),'main_big_before':big0,'main_big_after':big1,'main_big_reduction':float(1-big1/max(1,big0)),'out_events_before':obefore,'out_events_after':oafter,'out_event_reduction':float(1-oafter/max(1,obefore))}


def pack_nibbles(a):
    x=np.asarray(a,np.uint8).ravel()
    if x.size and np.max(x)>=16:raise RuntimeError('phase nibble range')
    out=np.zeros((x.size+1)//2,np.uint8);out[:]=(x[0::2]&15)
    if x.size>1:out[:x[1::2].size]|=(x[1::2]&15)<<4
    return out.tobytes()


def unpack_nibbles(b,n):
    z=np.frombuffer(b,np.uint8);x=np.empty(n,np.uint8);x[0::2]=z[:x[0::2].size]&15
    if n>1:x[1::2]=(z[:x[1::2].size]>>4)&15
    return x


def compress_phase(a):
    raw=pack_nibbles(a);best,allrows=best_comp(raw);n,m,b=best
    if decomp_one(b,m)!=raw:raise RuntimeError('phase backend roundtrip')
    return b,int(m),{'raw_nibble_bytes':len(raw),'compressed_bytes':len(b),'method':METHOD_NAMES[m],'nonzero_fraction':float(np.mean(np.asarray(a)!=0)) if np.asarray(a).size else 0.0,'all':allrows}


def choose_main(K):
    cache=structural_sequences(K);rows=[]
    for r2 in (0,1):
        for r9 in (0,1):
            b,parts=encode_main_candidate(K,r2,r9,cache);R=decode_main_candidate(b)
            if not np.array_equal(R,K):raise RuntimeError(('phase main exact K',r2,r9))
            rows.append((len(b),r2,r9,b,parts))
    rows.sort(key=lambda r:r[0]);return rows[0],[{'bytes':r[0],'inter_rice':bool(r[1]),'magnitude_rice':bool(r[2]),'parts':r[4]} for r in rows]


def decode_out_blob(blob,kind,td,Oshape):
    if kind==0:
        A=decode(blob).reshape(Oshape);return undelta(A,1) if td else A
    if kind==1:
        A=decode_out_sparse(blob);return undelta(A,1) if td else A
    raise RuntimeError(('outlier kind',kind))


def encode_phase_top(internal_eps,P,OP,mb,bo):
    pb,pm,pdiag=compress_phase(P);opb,opm,opdiag=compress_phase(OP);obb=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0
    h=struct.pack(PHHDR,PHMAG,float(internal_eps),NPH,pm,opm,(ok|(td<<1)),len(pb),len(opb),len(mb),len(obb))
    return h+pb+opb+mb+obb,{'phase_header_bytes':PHHS,'main_phase':pdiag,'out_phase':opdiag,'main_phase_bytes':len(pb),'out_phase_bytes':len(opb),'main_bytes':len(mb),'outlier_bytes':len(obb)}


def decode_phase_top(blob,main_shape,Oshape):
    q=struct.unpack(PHHDR,blob[:PHHS]);magic,eps,nph,pm,opm,ocode,lp,lop,lm,lo=q
    if magic!=PHMAG or nph!=NPH:raise RuntimeError('phase top header')
    p=PHHS;pb=blob[p:p+lp];p+=lp;opb=blob[p:p+lop];p+=lop;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('phase top length')
    pr=decomp_one(pb,pm);opr=decomp_one(opb,opm);P=unpack_nibbles(pr,int(np.prod(main_shape))).reshape(main_shape);OP=unpack_nibbles(opr,Oshape[0]);RK=decode_main_candidate(mb);ok=ocode&1;td=(ocode>>1)&1;RO=decode_out_blob(obb,ok,td,Oshape)
    return float(eps),P,OP,RK,RO


def reconstruct(Xshape,tm,outids,Qgrid,O,P,OP,step):
    Y=np.empty(Xshape,np.float32);s32=np.float32(step)
    for tid,c,l,s in tm:
        phi=np.float32(step*(int(P[c,l,s])/NPH));Y[tid]=phi+Qgrid[c,l,s].astype(np.float32)*s32
    for j,tid in enumerate(outids.tolist()):
        phi=np.float32(step*(int(OP[j])/NPH));Y[tid]=phi+O[j].astype(np.float32)*s32
    return Y


def baseline_current(X,tm,outids,shape,public_eps,internal_eps):
    step=2*internal_eps;G=np.zeros(shape,np.int32)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid].astype(np.float64)/step).astype(np.int32)
    O=np.rint(X[outids].astype(np.float64)/step).astype(np.int32);K=delta(G,3);bm,_=choose_main(K);bo=best_out(O);container=TOP_HS+bm[0]+int(bo[0])
    return {'container_bytes':int(container),'main_bytes':int(bm[0]),'outlier_bytes':int(bo[0]),'K_nonzero_fraction':float(np.mean(K!=0)),'inter_rice':bool(bm[1]),'magnitude_rice':bool(bm[2])}


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy)
    incumbent=baseline_current(X,tm,outids,G0.shape,public_eps,internal_eps)
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step);K=delta(G,3);bm,cands=choose_main(K);bo=best_out(O);top,tdiag=encode_phase_top(internal_eps,P,OP,bm[3],bo)
    ee,DP,DOP,RK,RO=decode_phase_top(top,G.shape[:-1],O.shape);RG=undelta(RK,3)
    if not np.array_equal(RK,K) or not np.array_equal(RO,O) or not np.array_equal(DP,P) or not np.array_equal(DOP,OP):raise RuntimeError('phase exact byte decode')
    Y=reconstruct(X.shape,tm,outids,RG,RO,DP,DOP,2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'nphase':NPH,'raw_bytes':raw,'geometry':geom,'phase_diag':pdiag,'phase_container_bytes':len(top),'phase_ratio':float(raw/len(top)),'phase_gain_vs_direct_sz3':float(szb/len(top)),'phase_K_nonzero_fraction':float(np.mean(K!=0)),'phase_main_choice':{'bytes':bm[0],'inter_rice':bool(bm[1]),'magnitude_rice':bool(bm[2]),'parts':bm[4]},'phase_main_candidates':cands,'phase_accounting':tdiag,'incumbent':incumbent,'improvement_vs_incumbent_bytes':int(incumbent['container_bytes']-len(top)),'improvement_vs_incumbent_percent':float(100*(incumbent['container_bytes']-len(top))/incumbent['container_bytes']),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6))}
    if not out['valid']:raise RuntimeError(('phase hard error',me,public_eps,internal_eps))
    print(json.dumps({'frac':frac,'incumbent_bytes':incumbent['container_bytes'],'phase_bytes':len(top),'improvement_bytes':out['improvement_vs_incumbent_bytes'],'improvement_percent':out['improvement_vs_incumbent_percent'],'event_reduction':pdiag['main_event_reduction'],'K_before':incumbent['K_nonzero_fraction'],'K_after':out['phase_K_nonzero_fraction'],'gain_sz3':out['phase_gain_vs_direct_sz3'],'maxerr':me,'eps':public_eps},indent=2),flush=True);json.dump(out,open('soda_tight_phase_rice.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
