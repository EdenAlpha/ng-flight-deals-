import json,struct,sys
import numpy as np
import soda_record_header_transform as hdr
import soda_intergap_context_refine as ctx

base=hdr.base
S2MAG=b'SRS16701'; S2HDR='<8sdBBQQ'; S2HS=struct.calcsize(S2HDR)
ORDER=(0,1,2); CONTEXT_KIND=3


def encode_samples_refined(X,gx,gy,internal_eps):
    step=2*internal_eps;G,tm,outids,geom=ctx.geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=ctx.delta(G,3)
    cache=ctx.prepare_common(K,ORDER);common=ctx.compress_common(cache[2]);mb,parts=ctx.encode_kind(K,CONTEXT_KIND,ORDER,cache,common);RK=ctx.decode_kind(mb)
    if not np.array_equal(RK,K):raise RuntimeError('refined main K encode audit')
    bo=ctx.best_out(O);obb=bo[6];out_kind=0 if bo[1]=='gap' else 1;tdiff=1 if bo[2] else 0;RO=ctx.decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('refined outlier encode audit')
    h=struct.pack(S2HDR,S2MAG,float(internal_eps),out_kind,tdiff,len(mb),len(obb))
    diag={'main_bytes':len(mb),'outlier_bytes':len(obb),'sample_header_bytes':S2HS,'main_parts':parts,'context_kind':CONTEXT_KIND,'context_name':ctx.context_name(CONTEXT_KIND),'outlier_kind':bo[1],'outlier_tdiff':bool(bo[2]),'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0))}
    return h+mb+obb,diag


def decode_samples_refined(blob,ntr,ns,gx,gy):
    if len(blob)<S2HS:raise RuntimeError('short refined sample blob')
    magic,eps,ok,td,lm,lo=struct.unpack(S2HDR,blob[:S2HS])
    if magic!=S2MAG:raise RuntimeError('bad refined sample magic')
    p=S2HS;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('refined sample blob length')
    RK=ctx.decode_kind(mb);RG=ctx.undelta(RK,3);dummy=np.empty((ntr,ns),np.float32);_,tm,outids,geom=ctx.geometry_map(dummy,gx,gy);Oshape=(len(outids),ns)
    if ok==0:
        A=ctx.decode(obb).reshape(Oshape);RO=ctx.undelta(A,1) if td else A
    elif ok==1:
        A=ctx.decode_out_sparse(obb);RO=ctx.undelta(A,1) if td else A
    else:raise RuntimeError('bad refined outlier kind')
    Y=np.empty((ntr,ns),np.float32)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*eps)
    Y[outids]=RO.astype(np.float32)*np.float32(2*eps)
    return Y,float(eps),geom

base.encode_samples=encode_samples_refined
base.decode_samples=decode_samples_refined

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    base.main(sys.argv[1],sys.argv[2],sys.argv[3])
