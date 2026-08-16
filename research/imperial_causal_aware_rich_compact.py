import json,sys,struct
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_compact_nova as qc
import imperial_causal_context_surface as rich
import imperial_compact_ar32_audit as car

VERSION=2


def compact_rich_defect(D):
    A=np.asarray(D,np.int32);u=x.m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray([nb]);detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for mode in rich.MODES:
            for order in rich.ORDERS:
                old,d=rich.encode_plane(B,known,bit,mode,order)
                mi,oi,nbits,L=struct.unpack_from('<BBII',old,0);cm=int(old[10]);store=old[11:11+L]
                if 11+L!=len(old) or L>=16384:raise RuntimeError(('rich plane frame',bit,L))
                rem=int(nbits)&7
                meta=(int(mi)&15)|((int(oi)&1)<<4)|((cm&1)<<5)|((rem&7)<<6)|(int(L)<<9)
                payload=int(meta).to_bytes(3,'little')+store
                if best is None or len(payload)<len(best[0]):best=(payload,{'bit':bit,'mode':mode,'order':order,'payload_bytes':L,'arith_bits':int(nbits),'compressed':bool(cm),'compact_bytes':len(payload),'ones':int(B.sum())})
        payload,d=best;out.extend(payload);detail.append(d);known|=B.astype(np.uint64)<<bit
    return bytes(out),detail


def decode_compact_rich(buf,pos,shape):
    if pos>=len(buf):raise RuntimeError('rich eof')
    nb=int(buf[pos]);pos+=1;uu=np.zeros(shape,np.uint64)
    for bit in range(nb-1,-1,-1):
        if pos+3>len(buf):raise RuntimeError('rich meta eof')
        meta=int.from_bytes(buf[pos:pos+3],'little');pos+=3
        mi=meta&15;oi=(meta>>4)&1;cm=(meta>>5)&1;rem=(meta>>6)&7;L=(meta>>9)&0x3fff
        if mi>=len(rich.MODES) or oi>=len(rich.ORDERS):raise RuntimeError(('rich selector',mi,oi))
        store=bytes(buf[pos:pos+L]);pos+=L
        if len(store)!=L:raise RuntimeError('rich payload eof')
        raw=x.m.D.decompress(store) if cm else store
        if not raw:raise RuntimeError('rich empty arithmetic')
        nbits=len(raw)*8 if rem==0 else (len(raw)-1)*8+rem
        mode=rich.MODES[mi];order=rich.ORDERS[oi];cur=np.zeros(shape,np.uint8)
        _,nctx=rich.ctx_id(uu,cur,0,0,bit,mode);z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ad=x.rr.ArithDecoder(raw,nbits)
        for c0,t0 in rich.iter_coords(shape,order):
            k,_=rich.ctx_id(uu,cur,c0,t0,bit,mode);b=ad.decode(int(z[k]),int(o[k]));cur[c0,t0]=b
            if b:o[k]+=1
            else:z[k]+=1
        uu|=cur.astype(np.uint64)<<bit
    return x.m.unzig(uu).astype(np.int32),pos


def compact_ar32_bytes(X,eps):
    old=x.g.ar32_baseline(X,eps);co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);kf,kdetail=car.encode_k_compact(K);stream=bytes([car.VERSION])+model+kf
    pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=car.decode_k_compact(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError('compact AR trailing')
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)) or not np.array_equal(Kd,K):raise RuntimeError('compact AR field mismatch')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('compact AR reconstruction mismatch')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'innovation_bytes':len(kf),'model_rep':mname,'maxerr':me,'old_bytes':old['bytes']}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);ar32=compact_ar32_bytes(X,eps)
    h,Q,D,dts,dcs,co,intercept,search=qc.reproduce_causal_best(X,eps)
    # Actual rich framed comparator on exactly the causal-aware Q field.
    fb,_,FD,fdetail=rich.frame(D);framed=x.c.validate(X,eps,h,Q,FD,dts,dcs,co,intercept,fb,'causal_aware_rich_framed',fdetail)
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);defect,ddetail=compact_rich_defect(D);stream=bytes([VERSION])+model+defect
    pos=0
    if stream[pos]!=VERSION:raise RuntimeError('version')
    pos+=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('compact rich parse/defect mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('compact rich Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('NOVA hard',me,eps))
    nova={'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'version_bytes':1,'maxerr':me,'delta_vs_compact_ar32':len(stream)-ar32['bytes'],'gain_vs_compact_ar32':ar32['bytes']/len(stream),'gain_vs_sz3':szb/len(stream),'delta_vs_rich_framed':len(stream)-framed['bytes']}
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'compact_ar32':ar32,'rich_framed':framed,'compact_nova':nova,'search':search,'model_detail':md,'defect_detail':ddetail,'scope':'Head-to-head decoder-real compact comparison on the identical hard Imperial 32x1024 object. NOVA reproduces PR546 causal-address-aware legal reconstruction, then searches PR541 richer public decoder-shared causal contexts per bitplane and serializes them with a 3-byte packed plane header (mode/order/compression/final-bit-count/payload-length), exact combinatorial tap-set rank, and signed-varint coefficients. AR32 is independently rebuilt and compacted in the same process under the same external shape/epsilon convention. Both literal streams are parsed to EOF, exact internal fields/reconstructions are replayed, and unchanged hard-error checks are mandatory. No stale comparator or surrogate byte count is used.'}
    json.dump(out,open('imperial_causal_aware_rich_compact.json','w'),indent=2)
    print(json.dumps({'summary':{'rich_framed':framed['bytes'],'compact_nova':nova['bytes'],'compact_ar32':ar32['bytes'],'delta':nova['delta_vs_compact_ar32'],'gain_ar32':nova['gain_vs_compact_ar32'],'sz3':int(szb),'model':nova['model_bytes'],'defect':nova['defect_bytes'],'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
