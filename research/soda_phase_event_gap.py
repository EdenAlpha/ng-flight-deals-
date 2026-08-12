import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the audited PR #126 geometry + event-gap codec exactly.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

PMAG=b'PHEGv001'; PH='<8sBddI5Q'; PHS=struct.calcsize(PH)


def choose_trace_phase(x,step,nph):
    # Frozen PR #120 objective: minimize event count first, then >1 jumps,
    # total absolute jump magnitude, and phase index. Each candidate remains
    # inside step/2 = internal_eps of the source before float roundoff.
    best=None
    xd=x.astype(np.float64)
    for k in range(nph):
        phi=step*(k/nph)
        q=np.rint((xd-phi)/step).astype(np.int32)
        d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1]
        score=(int(np.count_nonzero(d)),int(np.count_nonzero(np.abs(d)>1)),int(np.abs(d,dtype=np.int64).sum()),k)
        if best is None or score<best[0]:best=(score,k,q)
    return best[1],best[2]


def phase_quantize(X,tm,outids,shape,step,nph):
    G=np.zeros(shape,np.int32);P=np.zeros(shape[:-1],np.uint8);before=after=0
    for tid,c,l,s in tm:
        q0=np.rint(X[tid].astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];before+=int(np.count_nonzero(d0))
        k,q=choose_trace_phase(X[tid],step,nph);P[c,l,s]=k;G[c,l,s]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];after+=int(np.count_nonzero(d))
    O=np.zeros((len(outids),X.shape[1]),np.int32);OP=np.zeros(len(outids),np.uint8);obefore=oafter=0
    for j,tid in enumerate(outids.tolist()):
        q0=np.rint(X[tid].astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];obefore+=int(np.count_nonzero(d0))
        k,q=choose_trace_phase(X[tid],step,nph);OP[j]=k;O[j]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];oafter+=int(np.count_nonzero(d))
    return G,P,O,OP,{'main_events_before':before,'main_events_after':after,'main_event_reduction':1-after/max(before,1),'out_events_before':obefore,'out_events_after':oafter,'out_event_reduction':1-oafter/max(obefore,1)}


def best_gap_main(K):
    rows=[]
    for order in itertools.permutations((0,1,2)):
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K,order,vm,level);R=decode(b)
                if not np.array_equal(R,K):raise RuntimeError('phase gap main decode')
                rows.append((len(b),order,vm,level,b,parts))
    rows.sort(key=lambda x:x[0]);return rows[0],rows


def best_gap_out(O):
    rows=[]
    # Phase-adjusted O is already a state sequence; PR #126 legitimately compares
    # direct and time-differenced event-gap forms plus prior generic sparse modes.
    for td in (False,True):
        A=delta(O,1) if td else O;K4=A.reshape(1,1,A.shape[0],A.shape[1])
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K4,(0,1,2),vm,level);R=decode(b).reshape(O.shape);RR=undelta(R,1) if td else R
                if not np.array_equal(RR,O):raise RuntimeError('phase gap out decode')
                rows.append((len(b),'gap',td,vm,level,None,b,parts))
        for level in (19,22):
            for perm in ((0,1,2,3),(3,1,2,0)):
                for rep in (0,1,2):
                    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
                    if not np.array_equal(RR,O):raise RuntimeError('phase generic out decode')
                    rows.append((len(b),'generic',td,rep,level,perm,b,{}))
    rows.sort(key=lambda x:x[0]);return rows[0],rows


def encode_top(public_eps,internal_eps,nph,P,OP,mb,ob,outkind):
    zc=zstd.ZstdCompressor(level=22);pb=zc.compress(np.ascontiguousarray(P).tobytes());opb=zc.compress(np.ascontiguousarray(OP).tobytes());meta=struct.pack('<4I',*P.shape,int(OP.size))
    h=struct.pack(PH,PMAG,int(nph),float(public_eps),float(internal_eps),int(outkind),len(meta),len(pb),len(opb),len(mb),len(ob))
    return h+meta+pb+opb+mb+ob,{'meta':len(meta),'phase_main':len(pb),'phase_out':len(opb),'top_header':PHS}


def decode_top(blob,main_order,bo):
    magic,nph,public_eps,internal_eps,outkind,lmeta,lp,lop,lm,lo=struct.unpack(PH,blob[:PHS])
    if magic!=PMAG:raise RuntimeError('phase-gap magic')
    p=PHS;meta=blob[p:p+lmeta];p+=lmeta;C,L,S,N=struct.unpack('<4I',meta);pb=blob[p:p+lp];p+=lp;opb=blob[p:p+lop];p+=lop;mb=blob[p:p+lm];p+=lm;ob=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('phase-gap top length')
    zd=zstd.ZstdDecompressor();P=np.frombuffer(zd.decompress(pb),np.uint8,count=C*L*S).reshape(C,L,S);OP=np.frombuffer(zd.decompress(opb),np.uint8,count=N)
    K=decode(mb);Oblob=ob
    if outkind==0:
        A=decode(Oblob).reshape(N,-1);O=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(Oblob);O=undelta(A,1) if bo[2] else A
    return int(nph),float(public_eps),float(internal_eps),P,OP,K,O


def main(path):
    nph=16
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=.1*std;internal_eps=public_eps*(1-1e-4);step=2*internal_eps;raw=X.nbytes
    G0,tm,outids,geom=geometry_map(X,gx,gy);G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step,nph);K=delta(G,3)
    bm,mcands=best_gap_main(K);bo,ocands=best_gap_out(O);mb=bm[4];ob=bo[6];outkind=0 if bo[1]=='gap' else 1
    blob,over=encode_top(public_eps,internal_eps,nph,P,OP,mb,ob,outkind)
    nn,pe,ie,DP,DOP,RK,RO=decode_top(blob,bm[1],bo);RG=undelta(RK,3);Y=np.empty_like(X);dstep=np.float32(2*ie)
    for tid,c,l,s in tm:
        phi=np.float32((2*ie)*(int(DP[c,l,s])/nn));Y[tid]=phi+RG[c,l,s].astype(np.float32)*dstep
    for j,tid in enumerate(outids.tolist()):
        phi=np.float32((2*ie)*(int(DOP[j])/nn));Y[tid]=phi+RO[j].astype(np.float32)*dstep
    me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps)
    rows=[]
    for r in mcands[:12]:rows.append({'bytes':r[0],'order':list(r[1]),'mode':'signed' if r[2]==0 else 'signmag','level':r[3],'parts':r[5]})
    om=[]
    for r in ocands[:10]:om.append({'bytes':r[0],'kind':r[1],'tdiff':r[2],'mode':r[3],'level':r[4],'perm':list(r[5]) if r[5] is not None else None,'parts':r[7]})
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'public_eps':public_eps,'internal_eps':internal_eps,'nphase':nph,'geometry':geom,'phase_diag':pdiag,'phase_main_nonzero_fraction':float(np.mean(P!=0)),'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':rows[0],'main_candidates':rows,'outlier_best':om[0],'outlier_candidates':om,'phase_overhead':over,'container_bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(blob),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(blob),'two_x_gate_bytes':133225/2}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_phase_event_gap.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
