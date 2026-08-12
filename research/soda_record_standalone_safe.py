import importlib.util,struct,sys
import numpy as np

spec=importlib.util.spec_from_file_location('soda_record_standalone_impl','research/soda_record_standalone.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

# The imported PR161 stack deliberately shares one module global namespace.
# Restore its sparse-array SHS, and keep the outer sample-wrapper size private.
SAMPLE_HS=struct.calcsize(m.SAMP_HDR)
m.SHS=struct.calcsize(m.SH)

def encode_samples(X,gx,gy,internal_eps):
    step=2*internal_eps;G,tm,outids,geom=m.geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=m.delta(G,3);mb,parts=m.encode_main(K,(0,1,2),4);RK=m.decode_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('main K encode audit')
    bo=m.best_out(O);obb=bo[6];out_kind=0 if bo[1]=='gap' else 1;tdiff=1 if bo[2] else 0
    if out_kind==0:A=m.decode(obb).reshape(O.shape);RO=m.undelta(A,1) if tdiff else A
    else:A=m.decode_out_sparse(obb);RO=m.undelta(A,1) if tdiff else A
    if not np.array_equal(RO,O):raise RuntimeError('outlier encode audit')
    h=struct.pack(m.SAMP_HDR,m.SAMP_MAGIC,float(internal_eps),out_kind,tdiff,len(mb),len(obb))
    diag={'main_bytes':len(mb),'outlier_bytes':len(obb),'sample_header_bytes':SAMPLE_HS,'main_parts':parts,'outlier_kind':bo[1],'outlier_tdiff':bool(bo[2]),'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0))}
    return h+mb+obb,diag

def decode_samples(blob,ntr,ns,gx,gy):
    if len(blob)<SAMPLE_HS:raise RuntimeError('short sample blob')
    magic,eps,ok,td,lm,lo=struct.unpack(m.SAMP_HDR,blob[:SAMPLE_HS])
    if magic!=m.SAMP_MAGIC:raise RuntimeError('bad sample magic')
    p=SAMPLE_HS;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('sample blob length')
    RK=m.decode_main(mb);RG=m.undelta(RK,3);dummy=np.empty((ntr,ns),np.float32);_,tm,outids,geom=m.geometry_map(dummy,gx,gy);Oshape=(len(outids),ns)
    if ok==0:A=m.decode(obb).reshape(Oshape);RO=m.undelta(A,1) if td else A
    elif ok==1:A=m.decode_out_sparse(obb);RO=m.undelta(A,1) if td else A
    else:raise RuntimeError('bad outlier kind')
    Y=np.empty((ntr,ns),np.float32)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*eps)
    Y[outids]=RO.astype(np.float32)*np.float32(2*eps)
    return Y,float(eps),geom

m.encode_samples=encode_samples
m.decode_samples=decode_samples

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    m.main(sys.argv[1],sys.argv[2],sys.argv[3])
