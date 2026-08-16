import json,sys,struct
import h5py,numpy as np
import imperial_ar8_adaptive_context_address as a
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

a.P=1
a.TRAIN=64
STEP=267
HEADER=32
SELECTOR=1
SCANS=('t_c_fwd','t_c_rev','t_snake_c','c_t_fwd','c_t_rev','c_snake_t','trev_c_fwd','trev_c_rev')
CFAMS=('global','prefix','prev1','prefix_prev1','prev2','prefix_prev2','card','prefix_card','diag','prefix_diag','card_prev','prefix_card_prev')


def scan_coords(shape,sid):
    nc,nt=shape;out=[]
    if sid==0:
        for t in range(nt):
            for c in range(nc):out.append((c,t))
    elif sid==1:
        for t in range(nt):
            for c in range(nc-1,-1,-1):out.append((c,t))
    elif sid==2:
        for t in range(nt):
            it=range(nc) if (t&1)==0 else range(nc-1,-1,-1)
            for c in it:out.append((c,t))
    elif sid==3:
        for c in range(nc):
            for t in range(nt):out.append((c,t))
    elif sid==4:
        for c in range(nc):
            for t in range(nt-1,-1,-1):out.append((c,t))
    elif sid==5:
        for c in range(nc):
            it=range(nt) if (c&1)==0 else range(nt-1,-1,-1)
            for t in it:out.append((c,t))
    elif sid==6:
        for t in range(nt-1,-1,-1):
            for c in range(nc):out.append((c,t))
    elif sid==7:
        for t in range(nt-1,-1,-1):
            for c in range(nc-1,-1,-1):out.append((c,t))
    else:raise ValueError(sid)
    return out


def _neighbor_code(B,V,c,t,diag=False):
    nc,nt=B.shape
    pts=((c-1,t),(c+1,t),(c,t-1),(c,t+1)) if not diag else ((c-1,t-1),(c+1,t-1),(c-1,t+1),(c+1,t+1))
    code=0
    for cc,tt in pts:
        v=2
        if 0<=cc<nc and 0<=tt<nt and V[cc,tt]:v=int(B[cc,tt])
        code=code*3+v
    return code


def ctx_key(known,B,V,bit,c,t,hist,cid):
    fam=CFAMS[cid];prefix=int(known[c,t]>>(bit+1));p1=int(hist[-1]) if hist else 2;p2=int(hist[-2]) if len(hist)>1 else 2
    if fam=='global':return 0
    if fam=='prefix':return prefix
    if fam=='prev1':return p1
    if fam=='prefix_prev1':return prefix*3+p1
    if fam=='prev2':return p1*3+p2
    if fam=='prefix_prev2':return prefix*9+p1*3+p2
    card=_neighbor_code(B,V,c,t,False)
    if fam=='card':return card
    if fam=='prefix_card':return prefix*81+card
    diag=_neighbor_code(B,V,c,t,True)
    if fam=='diag':return diag
    if fam=='prefix_diag':return prefix*81+diag
    if fam=='card_prev':return card*3+p1
    if fam=='prefix_card_prev':return prefix*243+card*3+p1
    raise ValueError(fam)


def encode_scan(B,known,bit,sid,cid):
    ae=rr.ArithEncoder();counts={};V=np.zeros(B.shape,np.uint8);hist=[]
    for c,t in scan_coords(B.shape,sid):
        k=ctx_key(known,B,V,bit,c,t,hist,cid);z,o=counts.get(k,(1,1));b=int(B[c,t]);ae.encode(b,z,o)
        counts[k]=(z,o+1) if b else (z+1,o);Bv=b;V[c,t]=1;hist.append(Bv)
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    idx=sid*len(CFAMS)+cid;tag=16+idx
    payload=struct.pack('<BBII',tag,am,int(nbits),len(astore))+astore
    return payload,{'kind':'scan_adaptive','scan':SCANS[sid],'family':CFAMS[cid],'groups':len(counts),'arith_bytes':len(astore),'arith_bits':int(nbits),'stored':len(payload),'ones':int(B.sum())}


def decode_scan(buf,off,known,bit,tag,shape):
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9;astore=buf[off:off+alen];off+=alen;araw=m.D.decompress(astore) if am else astore
    idx=tag-16;sid=idx//len(CFAMS);cid=idx%len(CFAMS)
    if sid>=len(SCANS):raise RuntimeError(('scan tag',tag))
    ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);V=np.zeros(shape,np.uint8);hist=[];counts={}
    for c,t in scan_coords(shape,sid):
        k=ctx_key(known,B,V,bit,c,t,hist,cid);z,o=counts.get(k,(1,1));b=ad.decode(z,o);B[c,t]=b;V[c,t]=1;hist.append(int(b));counts[k]=(z,o+1) if b else (z+1,o)
    return B,off


def frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'SRA1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'kind':'rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for sid in range(len(SCANS)):
            for cid in range(len(CFAMS)):
                payload,d=encode_scan(B,known,bit,sid,cid);row=(payload,d)
                if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'SRA1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=buf[off];off+=1
        if tag<16:B,off=a.decode_rank_payload(buf,off,uu,bit,tag,A.shape)
        else:B,off=decode_scan(buf,off,uu,bit,tag,A.shape)
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('scan frame replay')
    return len(buf),Ad,detail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=a.build_ar8(X,eps)
    baseb,_,baseK,baseD=a.hybrid_frame(K);sb,SK,sd=frame(K)
    if not np.array_equal(baseK,K) or not np.array_equal(SK,K):raise RuntimeError('K replay')
    mer=a.replay(X,eps,cd,SK,R);base_total=mb+baseb+HEADER+SELECTOR;total=mb+sb+HEADER+SELECTOR
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':1,'train':64,'step':STEP,'model_bytes':mb,'base_adaptive':{'bytes':base_total,'payload_bytes':baseb,'detail':baseD},'scan_address':{'bytes':total,'payload_bytes':sb,'maxerr':mer,'detail':sd,'gain_vs_base':base_total/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total},'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'scans':list(SCANS),'context_families':list(CFAMS),'scope':'Decoder-real Session-Seeded-GPS-style coordinate search on AR1/train64/step267. For each K bitplane the encoder searches a fixed public family of reversible scan coordinate systems plus causal adaptive context grammars, and transmits only the winning tagged arithmetic stream. Every context depends solely on already decoded same-plane symbols, already decoded higher planes, and public coordinates/scan ID. No learned probability table or search trajectory is transmitted. Rank coding remains available as fallback. The selected stream byte-decodes the exact K field, causally replays the charged AR1 reconstruction and rechecks the unchanged hard source error.'}
    json.dump(out,open('imperial_ar1_scan_coordinate_address.json','w'),indent=2)
    print(json.dumps({'summary':{'base_adaptive':base_total,'scan_address':total,'delta':total-base_total,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_base':base_total/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total}},indent=2),flush=True)
    for x in sd:print(json.dumps(x),flush=True)

if __name__=='__main__':main(sys.argv[1])
