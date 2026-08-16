import json,sys
import h5py,numpy as np
import imperial_causal_context_surface as rich
import imperial_causal_aware_compact_nova as qc
import imperial_compact_nova_container as x
import imperial_compact_ar32_audit as car

CHAINS=(
 ('nbr5_mag4','nbr5','nbr3'),
 ('mag8_nbr5','nbr5','nbr3'),
 ('c2_mag4_nbr5','nbr5_mag4','nbr3'),
 ('prefix2_nbr5','nbr5','nbr3'),
)
THRESH=(4,8,16)
ORDERS=rich.ORDERS
VERSION_N=5
VERSION_A=6


def iter_coords(shape,order):return rich.iter_coords(shape,order)


def encode_plane(B,known,bit,ci,ti,oi):
    B=np.asarray(B,np.uint8);chain=CHAINS[ci];thr=THRESH[ti];order=ORDERS[oi];cur=np.zeros_like(B,np.uint8);zs=[];os=[]
    for mode in chain:
        _,nctx=rich.ctx_id(known,cur,0,0,bit,mode);zs.append(np.ones(nctx,np.int64));os.append(np.ones(nctx,np.int64))
    ae=x.rr.ArithEncoder()
    for c0,t0 in iter_coords(B.shape,order):
        keys=[]
        for mode in chain:keys.append(rich.ctx_id(known,cur,c0,t0,bit,mode)[0])
        level=len(chain)-1
        for j in range(len(chain)-1):
            k=keys[j]
            if int(zs[j][k]+os[j][k]-2)>=thr:level=j;break
        k=keys[level];b=int(B[c0,t0]);ae.encode(b,int(zs[level][k]),int(os[level][k]));cur[c0,t0]=b
        for j,kj in enumerate(keys):
            if b:os[j][kj]+=1
            else:zs[j][kj]+=1
    raw,nbits=ae.finish();zz=x.m.Z.compress(raw);cm=1 if len(zz)<len(raw) else 0;store=zz if cm else raw
    if len(store)>=16384:raise RuntimeError(('payload too large',len(store)))
    rem=int(nbits)&7;meta=(ci&3)|((ti&3)<<2)|((oi&1)<<4)|((cm&1)<<5)|((rem&7)<<6)|(len(store)<<9)
    return int(meta).to_bytes(3,'little')+store,{'chain':ci,'threshold':thr,'order':order,'compressed':bool(cm),'payload_bytes':len(store),'arith_bits':int(nbits),'stored':3+len(store),'ones':int(B.sum())}


def decode_plane(buf,pos,known,bit,shape):
    if pos+3>len(buf):raise RuntimeError('meta eof')
    meta=int.from_bytes(buf[pos:pos+3],'little');pos+=3;ci=meta&3;ti=(meta>>2)&3;oi=(meta>>4)&1;cm=(meta>>5)&1;rem=(meta>>6)&7;L=(meta>>9)&0x3fff
    if ci>=len(CHAINS) or ti>=len(THRESH):raise RuntimeError('selector')
    store=bytes(buf[pos:pos+L]);pos+=L
    if len(store)!=L:raise RuntimeError('payload eof')
    raw=x.m.D.decompress(store) if cm else store;nbits=len(raw)*8 if rem==0 else (len(raw)-1)*8+rem
    chain=CHAINS[ci];thr=THRESH[ti];order=ORDERS[oi];cur=np.zeros(shape,np.uint8);zs=[];os=[]
    for mode in chain:
        _,nctx=rich.ctx_id(known,cur,0,0,bit,mode);zs.append(np.ones(nctx,np.int64));os.append(np.ones(nctx,np.int64))
    ad=x.rr.ArithDecoder(raw,nbits)
    for c0,t0 in iter_coords(shape,order):
        keys=[rich.ctx_id(known,cur,c0,t0,bit,mode)[0] for mode in chain];level=len(chain)-1
        for j in range(len(chain)-1):
            k=keys[j]
            if int(zs[j][k]+os[j][k]-2)>=thr:level=j;break
        k=keys[level];b=ad.decode(int(zs[level][k]),int(os[level][k]));cur[c0,t0]=b
        for j,kj in enumerate(keys):
            if b:os[j][kj]+=1
            else:zs[j][kj]+=1
    return cur,pos


def encode_field(A):
    A=np.asarray(A,np.int32);u=x.m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64);out=bytearray([nb]);detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for ci in range(len(CHAINS)):
            for ti in range(len(THRESH)):
                for oi in range(len(ORDERS)):
                    p,d=encode_plane(B,known,bit,ci,ti,oi)
                    if best is None or len(p)<len(best[0]):best=(p,d)
        p,d=best;out.extend(p);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    return bytes(out),detail


def decode_field(buf,pos,shape):
    nb=int(buf[pos]);pos+=1;u=np.zeros(shape,np.uint64)
    for bit in range(nb-1,-1,-1):
        B,pos=decode_plane(buf,pos,u,bit,shape);u|=B.astype(np.uint64)<<bit
    return x.m.unzig(u).astype(np.int32),pos


def nova_stream(X,eps):
    h,Q,D,dts,dcs,co,intercept,search=qc.reproduce_causal_best(X,eps);model,_,_,_,_,_=x.compact_model(dts,dcs,co,intercept);field,detail=encode_field(D);stream=bytes([VERSION_N])+model+field
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32);DD,pos=decode_field(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('N field replay')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('N Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError('N hard')
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me},detail


def ar_stream(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);field,detail=encode_field(K);stream=bytes([VERSION_A])+model+field;pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=decode_field(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('A K replay')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('A R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError('A hard')
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me},detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);n,nd=nova_stream(X,eps);a,ad=ar_stream(X,eps);n['delta_vs_ar32']=n['bytes']-a['bytes'];n['gain_vs_ar32']=a['bytes']/n['bytes'];n['gain_vs_sz3']=szb/n['bytes']
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'nova':n,'ar32':a,'nova_detail':nd,'ar32_detail':ad,'scope':'Symmetric head-to-head using one identical generic lossless causal-backoff address coder on both NOVA learned-law defects and frozen AR32 innovations. Each bitplane adaptively backs off from detailed to broader public contexts until enough prior causal evidence exists; context counts and backoff decisions are deterministically decoder-shared, with only per-plane chain/threshold/order selector and arithmetic payload stored. NOVA and AR32 retain their distinct predictors/models and legal-reconstruction contracts. Both compact literal streams parse to EOF and replay exact internal fields/reconstructions under unchanged hard error. This isolates architectural gains from generic entropy-coder gains.'};json.dump(out,open('imperial_backoff_causal_headtohead.json','w'),indent=2)
    print(json.dumps({'summary':{'nova':n['bytes'],'ar32':a['bytes'],'delta':n['delta_vs_ar32'],'gain_ar32':n['gain_vs_ar32'],'sz3':int(szb),'nova_model':n['model_bytes'],'ar_model':a['model_bytes'],'nova_field':n['field_bytes'],'ar_field':a['field_bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
