import sys,json,struct
import h5py,numpy as np
import imperial_ar4_rich_adaptive_context_address as rich
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

a=rich.a
a.P=1
a.TRAIN=64
HEADER=32
SELECTOR=1
LOWBITS=3
LOWF=(
 'sub_global','partial','h','hbin','tres','cres','tcres','h_tres','h_tcres','hbin_tcres',
 'hc2_tcres','hpar_tcres','partial_tcres','partial_h_tcres','partial_hbin_tcres','u_prev_t','u_prev_tc'
)

def low_key(H,R,partial,sub,c,t,fam):
    h=int(H[c,t]);hb=max(0,h.bit_length()-1)
    rt=int(R[c,t-1]) if t>0 else 8
    rc=int(R[c-1,t]) if c>0 else 8
    ut=(int(H[c,t-1])<<LOWBITS | int(R[c,t-1])) if t>0 else -1
    uc=(int(H[c-1,t])<<LOWBITS | int(R[c-1,t])) if c>0 else -1
    if fam=='sub_global':return sub
    if fam=='partial':return (sub,partial)
    if fam=='h':return (sub,h)
    if fam=='hbin':return (sub,hb)
    if fam=='tres':return (sub,rt)
    if fam=='cres':return (sub,rc)
    if fam=='tcres':return (sub,rt,rc)
    if fam=='h_tres':return (sub,h,rt)
    if fam=='h_tcres':return (sub,h,rt,rc)
    if fam=='hbin_tcres':return (sub,hb,rt,rc)
    if fam=='hc2_tcres':return (sub,h>>1,rt,rc)
    if fam=='hpar_tcres':return (sub,h&1,hb,rt,rc)
    if fam=='partial_tcres':return (sub,partial,rt,rc)
    if fam=='partial_h_tcres':return (sub,partial,h,rt,rc)
    if fam=='partial_hbin_tcres':return (sub,partial,hb,rt,rc)
    if fam=='u_prev_t':return (sub,partial,ut)
    if fam=='u_prev_tc':return (sub,partial,ut,uc)
    raise ValueError(fam)

def encode_low(H,R,fid):
    fam=LOWF[fid];counts={};ae=rr.ArithEncoder();ones=[0,0,0]
    # time-major/channel-minor: both same-time previous-channel and previous-time same-channel are decoder-known.
    for t in range(R.shape[1]):
        for c in range(R.shape[0]):
            partial=0
            # Encode residue MSB->LSB inside each sample; current partial residue is then known to later subbits.
            for sub,bit in enumerate((2,1,0)):
                k=low_key(H,R,partial,sub,c,t,fam);z,o=counts.get(k,(1,1));b=(int(R[c,t])>>bit)&1
                ae.encode(b,z,o);ones[sub]+=b
                counts[k]=(z,o+1) if b else (z+1,o)
                partial=(partial<<1)|b
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    payload=struct.pack('<BBII',fid,am,int(nbits),len(astore))+astore
    return payload,{'family':fam,'groups':len(counts),'arith_bits':int(nbits),'arith_bytes':len(astore),'stored':len(payload),'ones_b2_b1_b0':ones}

def decode_low(buf,off,H,shape):
    fid,am,nbits,alen=struct.unpack_from('<BBII',buf,off);off+=10
    if fid>=len(LOWF):raise RuntimeError(('low fid',fid))
    astore=buf[off:off+alen];off+=alen;araw=m.D.decompress(astore) if am else astore
    fam=LOWF[fid];counts={};ad=rr.ArithDecoder(araw,nbits);R=np.zeros(shape,np.uint8)
    for t in range(shape[1]):
        for c in range(shape[0]):
            partial=0
            for sub,bit in enumerate((2,1,0)):
                k=low_key(H,R,partial,sub,c,t,fam);z,o=counts.get(k,(1,1));b=ad.decode(z,o)
                counts[k]=(z,o+1) if b else (z+1,o)
                partial=(partial<<1)|b
            R[c,t]=partial
    return R,off

def joint_frame(K):
    K=np.asarray(K,np.int32);U=m.zig(K);mx=int(U.max()) if U.size else 0;nb=max(LOWBITS+1,mx.bit_length())
    H=U>>LOWBITS;known=np.zeros_like(U,np.uint64)
    # Physical frame: header, high bitplanes using proven rich chooser, then one joint low-residue stream.
    out=bytearray(struct.pack('<4sHHBB',b'JLR1',K.shape[0],K.shape[1],nb,LOWBITS));detail_hi=[]
    for bit in range(nb-1,LOWBITS-1,-1):
        B=((U>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'kind':'rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(a.ADAPT)):
            payload,d=a.encode_adaptive(B,known,bit,afid);row=(payload,{'kind':'adaptive',**d})
            if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail_hi.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    R=(U&7).astype(np.uint8);bestlow=None
    for fid in range(len(LOWF)):
        payload,d=encode_low(H,R,fid);row=(payload,d)
        if bestlow is None or len(payload)<len(bestlow[0]):bestlow=row
    out.extend(bestlow[0]);lowdetail=bestlow[1]
    buf=bytes(out);off=0;magic,nc,nt,nb2,lb=struct.unpack_from('<4sHHBB',buf,off);off+=10
    if magic!=b'JLR1' or (nc,nt)!=K.shape or nb2!=nb or lb!=LOWBITS:raise RuntimeError('joint header')
    Ud=np.zeros_like(U,np.uint64)
    for bit in range(nb-1,LOWBITS-1,-1):
        tag=buf[off];off+=1
        if tag<16:B,off=a.decode_rank_payload(buf,off,Ud,bit,tag,K.shape)
        else:
            if tag>=16+len(a.ADAPT):raise RuntimeError(('high tag',tag))
            B,off=a.decode_adaptive_payload(buf,off,Ud,bit,tag,K.shape)
        Ud|=B.astype(np.uint64)<<bit
    Hd=Ud>>LOWBITS;Rd,off=decode_low(buf,off,Hd,K.shape);Ud|=Rd.astype(np.uint64)
    if off!=len(buf):raise RuntimeError(('joint trailing',off,len(buf)))
    Kd=m.unzig(Ud).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('joint K replay')
    return len(buf),'joint_low_residue',Kd,{'high':detail_hi,'low':lowdetail,'nbits':nb}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=a.build_ar8(X,eps)
    rb,rn,RK,rd=a.hybrid_frame(K);jb,jn,JK,jd=joint_frame(K)
    if not np.array_equal(RK,K) or not np.array_equal(JK,K):raise RuntimeError('K replay')
    rme=a.replay(X,eps,cd,RK,R);jme=a.replay(X,eps,cd,JK,R)
    rich_total=int(mb)+int(rb)+HEADER+SELECTOR;joint_total=int(mb)+int(jb)+HEADER+SELECTOR
    best=min(rich_total,joint_total);chosen='joint_low_residue' if joint_total<rich_total else 'rich_bitplanes'
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':1,'train':64,'step':267,'model_bytes':int(mb),'rich_bitplanes':{'bytes':rich_total,'payload_bytes':int(rb),'maxerr':rme,'detail':rd},'joint_low_residue':{'bytes':joint_total,'payload_bytes':int(jb),'maxerr':jme,'detail':jd},'chosen':chosen,'best_bytes':best,'delta_joint_vs_rich':joint_total-rich_total,'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'low_families':list(LOWF),'scope':'Decoder-real representation test on AR1/train64/step267. The proven PR600 rich bitplane stream is reproduced as a strict floor. The alternative decodes zigzag high bits first, then treats the three low zigzag bits jointly as one causal residue U mod 8 rather than three independent planes. The encoder tests a public family of residue-state contexts using already-decoded high quotient, current partial residue, previous-time residue, previous-channel residue and previous complete U states. Context counts start from fixed 1/1 priors and evolve identically at encoder/decoder; no probability table is transmitted. The selected low-residue family tag and physical arithmetic payload are charged. The complete K field is independently reconstructed, AR1 is causally replayed, and the unchanged source hard-error bound is verified.'}
    json.dump(out,open('imperial_ar1_joint_low_residue_address.json','w'),indent=2)
    print(json.dumps({'summary':{'rich':rich_total,'joint':joint_total,'delta':joint_total-rich_total,'chosen':chosen,'best':best,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'low':jd['low']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
