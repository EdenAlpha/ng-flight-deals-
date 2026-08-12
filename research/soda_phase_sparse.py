import itertools,json,os,struct,sys
import numpy as np,zstandard as zstd
# Reuse audited geometry/lattice routines.
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())
# Reuse audited sparse integer codec definitions without running its CLI.
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())

PMAG=b'PHSPv001'; PH='<8sBdI5Q'; PHS=struct.calcsize(PH)

def choose_trace_phase(x,step,nph):
    # All phases are modulo one lattice step; nearest-point quantization always has <= step/2 error.
    best=None
    for k in range(nph):
        phi=step*(k/nph)
        q=np.rint((x.astype(np.float64)-phi)/step).astype(np.int32)
        d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1]
        nz=int(np.count_nonzero(d)); big=int(np.count_nonzero(np.abs(d)>1)); mag=int(np.abs(d,dtype=np.int64).sum())
        score=(nz,big,mag,k)
        if best is None or score<best[0]:best=(score,k,q)
    return best[1],best[2]

def phase_quantize(X,tm,outids,shape,step,nph):
    G=np.zeros(shape,np.int32); P=np.zeros(shape[:-1],np.uint8)
    before=after=0
    for tid,c,l,s in tm:
        q0=np.rint(X[tid].astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];before+=int(np.count_nonzero(d0))
        k,q=choose_trace_phase(X[tid],step,nph);P[c,l,s]=k;G[c,l,s]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];after+=int(np.count_nonzero(d))
    O=np.zeros((len(outids),X.shape[1]),np.int32);OP=np.zeros(len(outids),np.uint8)
    obefore=oafter=0
    for j,tid in enumerate(outids.tolist()):
        q0=np.rint(X[tid].astype(np.float64)/step).astype(np.int32);d0=np.empty_like(q0);d0[0]=q0[0];d0[1:]=q0[1:]-q0[:-1];obefore+=int(np.count_nonzero(d0))
        k,q=choose_trace_phase(X[tid],step,nph);OP[j]=k;O[j]=q;d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];oafter+=int(np.count_nonzero(d))
    return G,P,O,OP,{'main_events_before':before,'main_events_after':after,'main_event_reduction':1-after/max(before,1),'out_events_before':obefore,'out_events_after':oafter,'out_event_reduction':1-oafter/max(obefore,1)}

def best_sparse(A):
    rows=[]
    for level in (19,22):
      for perm in itertools.permutations(range(4)):
        for rep in (0,1,2):
          b=encode_array(A,perm,rep,level);R=decode_array(b)
          if not np.array_equal(R,A):raise RuntimeError('sparse main decode')
          rows.append((len(b),level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'level':x[1],'perm':list(x[2]),'rep':['raw','sparse','ternary'][x[3]]} for x in rows],key=lambda r:r['bytes'])[:12]

def best_out(O):
    rows=[]
    for td in (False,True):
      A=delta(O,1) if td else O
      for level in (19,22):
       for perm in ((0,1,2,3),(3,1,2,0)):
        for rep in (0,1,2):
          b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
          if not np.array_equal(RR,O):raise RuntimeError('sparse out decode')
          rows.append((len(b),td,level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'tdiff':x[1],'level':x[2],'perm':list(x[3]),'rep':['raw','sparse','ternary'][x[4]]} for x in rows],key=lambda r:r['bytes'])[:12]

def encode_top(eps,nph,P,OP,mb,ob):
    zc=zstd.ZstdCompressor(level=22);pb=zc.compress(P.tobytes());opb=zc.compress(OP.tobytes());meta=struct.pack('<4I',*P.shape,OP.size)
    h=struct.pack(PH,PMAG,nph,float(eps),len(meta),len(pb),len(opb),len(mb),len(ob),0)
    return h+meta+pb+opb+mb+ob

def decode_top_phase(blob):
    magic,nph,eps,lmeta,lp,lop,lm,lo,_=struct.unpack(PH,blob[:PHS]);
    if magic!=PMAG:raise RuntimeError('phase magic')
    p=PHS;meta=blob[p:p+lmeta];p+=lmeta;C,L,S,N=struct.unpack('<4I',meta);pb=blob[p:p+lp];p+=lp;opb=blob[p:p+lop];p+=lop;mb=blob[p:p+lm];p+=lm;ob=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('phase top length')
    P=np.frombuffer(ZD.decompress(pb),np.uint8,count=C*L*S).reshape(C,L,S);OP=np.frombuffer(ZD.decompress(opb),np.uint8,count=N)
    K=decode_array(mb);ROA=decode_out_sparse(ob)
    return float(eps),int(nph),P,OP,K,ROA

path=sys.argv[1];nph=int(sys.argv[2]) if len(sys.argv)>2 else 16
X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=.1*std;internal_eps=public_eps*(1-1e-4);step=2*internal_eps;raw=X.nbytes
G0,tm,outids,geom=geometry_map(X,gx,gy);G,P,O,OP,diag=phase_quantize(X,tm,outids,G0.shape,step,nph)
K=delta(G,3);bm,cands=best_sparse(K);bo,ocands=best_out(O);mb=bm[4];ob=bo[5];top=encode_top(internal_eps,nph,P,OP,mb,ob)
ee,nn,DP,DOP,RK,ROA=decode_top_phase(top);RG=undelta(RK,3);RO=undelta(ROA,1) if bo[1] else ROA
recon=np.empty_like(X);dstep=np.float32(2*ee)
for tid,c,l,s in tm:
    phi=np.float32((2*ee)*(int(DP[c,l,s])/nn));recon[tid]=phi+RG[c,l,s].astype(np.float32)*dstep
for j,tid in enumerate(outids.tolist()):
    phi=np.float32((2*ee)*(int(DOP[j])/nn));recon[tid]=phi+RO[j].astype(np.float32)*dstep
me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,public_eps)
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'public_eps':public_eps,'internal_eps':internal_eps,'nphase':nph,'geometry':geom,'phase_diag':diag,'phase_main_nonzero_fraction':float(np.mean(P!=0)),'phase_blob_total_overhead_est':len(top)-len(mb)-len(ob),'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':ocands[0],'outlier_candidates':ocands,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=public_eps),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_sz3':float((raw/len(top))/(raw/szb))}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_phase_sparse.json','w'),indent=2)
