import itertools,json,os,struct,sys
import numpy as np
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())
HMAG=b'CHYBR001'; HH='<8sd4B4Q'; HHS=struct.calcsize(HH)
def repid(s):return {'raw':0,'sparse':1,'ternary':2}[s]
def best_lattice(A):
    rows=[]
    for level in (19,22):
      for perm in itertools.permutations(range(4)):
       for rep in (0,1,2):
        b=encode_array(A,perm,rep,level);R=decode_array(b)
        if not np.array_equal(R,A):raise RuntimeError('lattice decode')
        rows.append((len(b),level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'level':x[1],'perm':list(x[2]),'rep':['raw','sparse','ternary'][x[3]]} for x in rows],key=lambda r:r['bytes'])[:6]
def best_out_lattice(O):
    rows=[]
    for td in (False,True):
      A=delta(O,1) if td else O
      for level in (19,22):
       for perm in ((0,1,2,3),(3,1,2,0)):
        for rep in (0,1,2):
         b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
         if not np.array_equal(RR,O):raise RuntimeError('out lattice decode')
         rows.append((len(b),td,level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'tdiff':x[1],'level':x[2],'perm':list(x[3]),'rep':['raw','sparse','ternary'][x[4]]} for x in rows],key=lambda r:r['bytes'])[:6]
def sz_chunk(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);bb,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(bb,np.float32,A.shape);me=float(np.max(np.abs(A-R)));return np.asarray(bb,dtype=np.uint8).tobytes(),me
def sz_decode(chunk,shape):return sz.decompress(np.frombuffer(chunk,np.uint8),np.float32,shape)[0]
def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes
    G,tm,outids,geom=geometry_map(X,gx,gy)
    comp_maps=[[] for _ in range(G.shape[0])]
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32);comp_maps[c].append((tid,l,s))
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);modes=[];chunks=[];diag=[]
    for c in range(G.shape[0]):
        KL=K[c:c+1];lat,cands=best_lattice(KL);maps=sorted(comp_maps[c],key=lambda q:(q[1],q[2],q[0]));tids=np.asarray([q[0] for q in maps],np.int64);A=X[tids];sb,sme=sz_chunk(A,eps)
        if len(lat[4])<=len(sb):mode=0;chunk=lat[4];chosen='lattice'
        else:mode=1;chunk=sb;chosen='sz3'
        modes.append(mode);chunks.append(chunk);diag.append({'segment':f'component_{c}','trace_count':len(tids),'lattice_bytes':len(lat[4]),'lattice_best':cands[0],'sz3_bytes':len(sb),'sz3_maxerr':sme,'chosen':chosen,'chosen_bytes':len(chunk),'K_nonzero_fraction':float(np.mean(KL!=0))})
    outlat,ocands=best_out_lattice(O);olchunk=bytes([1 if outlat[1] else 0])+outlat[5];osz,osme=sz_chunk(X[outids],eps)
    if len(olchunk)<=len(osz):modes.append(2);chunks.append(olchunk);ochosen='lattice'
    else:modes.append(3);chunks.append(osz);ochosen='sz3'
    diag.append({'segment':'outliers','trace_count':len(outids),'lattice_bytes':len(olchunk),'lattice_best':ocands[0],'sz3_bytes':len(osz),'sz3_maxerr':osme,'chosen':ochosen,'chosen_bytes':len(chunks[-1])})
    top=struct.pack(HH,HMAG,float(eps),*modes,*[len(b) for b in chunks])+b''.join(chunks)
    # Full byte decode.
    magic,ee,*rest=struct.unpack(HH,top[:HHS]);dm=rest[:4];lens=rest[4:];p=HHS;ds=[]
    for L in lens:ds.append(top[p:p+L]);p+=L
    if magic!=HMAG or p!=len(top):raise RuntimeError('hybrid container')
    recon=np.empty_like(X)
    for c in range(G.shape[0]):
        maps=sorted(comp_maps[c],key=lambda q:(q[1],q[2],q[0]));tids=np.asarray([q[0] for q in maps],np.int64)
        if dm[c]==0:
            RKC=decode_array(ds[c]);RGC=undelta(RKC,3)
            for tid,l,s in maps:recon[tid]=RGC[0,l,s].astype(np.float32)*np.float32(2*ee)
        elif dm[c]==1:recon[tids]=sz_decode(ds[c],(len(tids),X.shape[1]))
        else:raise RuntimeError('component mode')
    if dm[3]==2:
        td=bool(ds[3][0]);ROA=decode_out_sparse(ds[3][1:]);RO=undelta(ROA,1) if td else ROA;recon[outids]=RO.astype(np.float32)*np.float32(2*ee)
    elif dm[3]==3:recon[outids]=sz_decode(ds[3],X[outids].shape)
    else:raise RuntimeError('out mode')
    me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'segments':diag,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_over_sz3':(raw/len(top))/(raw/szb)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_component_hybrid.json','w'),indent=2)
main(sys.argv[1])
