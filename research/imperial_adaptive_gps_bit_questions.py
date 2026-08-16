import json,sys,struct
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAMILIES=('global','last','state2','state3','last_c4','last_t8','last_ct2','last_neigh','state2_c4')


def state_keys(state,last,family):
    flat=np.asarray(state,np.uint16).ravel();lf=np.asarray(last,np.uint8).ravel();nc,nt=state.shape
    cc=np.repeat(np.arange(nc,dtype=np.uint64),nt);tt=np.tile(np.arange(nt,dtype=np.uint64),nc)
    if family=='global':return np.zeros(flat.size,np.uint64)
    if family=='last':return lf.astype(np.uint64)
    if family=='state2':return (flat&3).astype(np.uint64)
    if family=='state3':return (flat&7).astype(np.uint64)
    if family=='last_c4':return lf.astype(np.uint64)*4+(cc*4//nc)
    if family=='last_t8':return lf.astype(np.uint64)*8+(tt*8//nt)
    if family=='last_ct2':return lf.astype(np.uint64)*4+(cc*2//nc)*2+(tt*2//nt)
    if family=='state2_c4':return (flat&3).astype(np.uint64)*4+(cc*4//nc)
    if family=='last_neigh':
        L=np.zeros_like(last);U=np.zeros_like(last);L[1:,:]=last[:-1,:];U[:,1:]=last[:,:-1]
        return lf.astype(np.uint64)*4+(L.ravel().astype(np.uint64)<<1)+U.ravel().astype(np.uint64)
    raise ValueError(family)


def encode_candidate(B,state,last,bit,fid):
    keys=state_keys(state,last,FAMILIES[fid]);order,starts,ends=rr.groups_for(keys);seq=np.asarray(B,np.uint8).ravel()[order]
    counts=bytearray();ks=[]
    for aa,zz in zip(starts,ends):
        k=int(seq[int(aa):int(zz)].sum());ks.append(k);rr.put_uvar(counts,k)
    craw=bytes(counts);cz=m.Z.compress(craw);cm=1 if len(cz)<len(craw) else 0;cstore=cz if cm else craw
    ae=rr.ArithEncoder()
    for aa,zz,k in zip(starts,ends,ks):
        rn=int(zz-aa);rk=int(k)
        for x in seq[int(aa):int(zz)]:
            b=int(x)
            if rk!=0 and rk!=rn:ae.encode(b,rn-rk,rk)
            rn-=1;rk-=b
    araw,nbits=ae.finish();az=m.Z.compress(araw);am=1 if len(az)<len(araw) else 0;astore=az if am else araw
    head=struct.pack('<BBBBIII',int(bit),fid,cm,am,len(cstore),int(nbits),len(astore))
    payload=head+cstore+astore
    return payload,{'bit':int(bit),'family':FAMILIES[fid],'groups':len(ks),'count_bytes':len(cstore),'arith_bytes':len(astore),'arith_bits':int(nbits),'ones':int(B.sum()),'stored':len(payload)}


def decode_candidate(payload,state,last,shape):
    off=0;bit,fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBBIII',payload,off);off+=16
    cstore=payload[off:off+clen];off+=clen;astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError('candidate trailing')
    craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
    keys=state_keys(state,last,FAMILIES[fid]);order,starts,ends=rr.groups_for(keys);ks=[];p=0
    for aa,zz in zip(starts,ends):
        k,p=rr.get_uvar(craw,p);n=int(zz-aa)
        if k>n:raise RuntimeError(('count',bit,k,n))
        ks.append(int(k))
    if p!=len(craw):raise RuntimeError('count trailing')
    ad=rr.ArithDecoder(araw,nbits);sorted_bits=np.empty(shape[0]*shape[1],np.uint8)
    for aa,zz,k in zip(starts,ends,ks):
        rn=int(zz-aa);rk=int(k)
        for j in range(int(aa),int(zz)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk:raise RuntimeError('rank remainder')
    flat=np.empty(sorted_bits.size,np.uint8);flat[order]=sorted_bits
    return int(bit),flat.reshape(shape)


def adaptive_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());remaining=list(range(nb));state=np.zeros(A.shape,np.uint16);last=np.zeros(A.shape,np.uint8)
    out=bytearray(struct.pack('<4sHHB',b'AGP1',A.shape[0],A.shape[1],nb));detail=[]
    for stage in range(nb):
        best=None
        for bit in remaining:
            B=((u>>bit)&1).astype(np.uint8)
            for fid in range(len(FAMILIES)):
                payload,d=encode_candidate(B,state,last,bit,fid)
                score=len(payload)
                if best is None or score<best[0]:best=(score,payload,d,B,bit)
        _,payload,d,B,bit=best
        out.extend(struct.pack('<I',len(payload)));out.extend(payload);detail.append({'stage':stage,**d});remaining.remove(bit);state=((state<<1)|B.astype(np.uint16));last=B
    buf=bytes(out);magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0);off=9
    if magic!=b'AGP1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('adaptive header')
    state=np.zeros(A.shape,np.uint16);last=np.zeros(A.shape,np.uint8);uu=np.zeros(A.shape,np.uint64);seen=set()
    for stage in range(nb):
        L=struct.unpack_from('<I',buf,off)[0];off+=4;payload=buf[off:off+L];off+=L;bit,B=decode_candidate(payload,state,last,A.shape)
        if bit in seen or bit<0 or bit>=nb:raise RuntimeError(('bit order',bit));seen.add(bit)
        uu|=B.astype(np.uint64)<<bit;state=((state<<1)|B.astype(np.uint16));last=B
    if off!=len(buf) or len(seen)!=nb:raise RuntimeError('adaptive trailing/order')
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('adaptive replay')
    return len(buf),'adaptive_gps_questions',Ad,detail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size);Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy())
    Q2,D2,_,changes=a.shape_search(Q2,lo,hi,D2,dts,dcs,co,intercept,g.SCALE,logc,a.NBITS,a.PASSES)
    rb,_,RE,rdetail=rr.restricted_rank_frame(D2);base=c.validate(X,eps,h,Q2,RE,dts,dcs,co,intercept,rb,'fixed_msb_rank',rdetail)
    ab,aname,AE,adetail=adaptive_frame(D2);adaptive=c.validate(X,eps,h,Q2,AE,dts,dcs,co,intercept,ab,aname,adetail)
    for r in (base,adaptive):
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    best=min((base,adaptive),key=lambda r:r['bytes'])
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'search_changes':int(changes),'base':base,'adaptive':adaptive,'best':best,'question_order':[x['bit'] for x in adetail],'question_detail':adetail,'scope':'Adaptive-GPS question-order codec over the exact PR518 address-shaped learned-law defect. Unlike PR512, no fixed MSB-to-LSB order is assumed. At each stage the encoder tries every undecoded zigzag defect bit and every small public context family built only from answers already decoded plus fixed coordinates, then physically stores the bit-ID, context selector, exact group counts and without-replacement arithmetic rank for the cheapest next question. The decoder reads the chosen question order from the stream, reconstructs the same contexts from prior decoded answers, recovers every plane and hence the identical signed defect raster. The charged learned generator then regenerates the exact Q field and the unchanged hard source error is verified. All adaptive choices are in the byte stream; there is no oracle or ideal entropy claim.'}
    json.dump(out,open('imperial_adaptive_gps_bit_questions.json','w'),indent=2)
    print(json.dumps({'summary':{'fixed':base['bytes'],'adaptive':adaptive['bytes'],'best':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'order':out['question_order'],'gain_ar32':arb['bytes']/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
