import sys,json,struct
import imperial_ar4_rich_adaptive_context_address as rich

a=rich.a
a.P=1
a.TRAIN=64
BASE=tuple(a.ADAPT)
OLD_ENCODE=a.encode_adaptive
OLD_DECODE=a.decode_adaptive_payload
SCALE=32768
MIXES={
 'mix_g_tc':('global','tc'),
 'mix_g3_tc':('global','global','global','tc'),
 'mix_g_pt_pc':('global','t','c','tc'),
 'mix_g_prefix':('global','prefix','prefix_t','prefix_tc'),
 'mix_g_temporal':('global','t','prefix_t','prefix_t2','prefix_tc_t2'),
 'mix_g_rich':('global','prefix_t','prefix_tc','prefix_tc_hpt','prefix_tc_hptc'),
 'mix_g_local_rich':('global','t','c','tc','prefix_t','prefix_tc','prefix_tc_diag'),
}
a.ADAPT=BASE+tuple(MIXES)

def mixed_freq(counts,keys):
    ps=0
    for d,k in zip(counts,keys):
        z,o=d.get(k,(1,1));tot=z+o
        p=(o*SCALE + tot//2)//tot
        if p<1:p=1
        elif p>=SCALE:p=SCALE-1
        ps+=p
    p=(ps+len(keys)//2)//len(keys)
    if p<1:p=1
    elif p>=SCALE:p=SCALE-1
    return SCALE-p,p

def encode_adaptive_mix(B,known,bit,afid):
    fam=a.ADAPT[afid]
    if fam not in MIXES:return OLD_ENCODE(B,known,bit,afid)
    experts=MIXES[fam];counts=[{} for _ in experts];ae=a.rr.ArithEncoder()
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            keys=[a.akey(known,B,bit,c,t,e) for e in experts];z,o=mixed_freq(counts,keys);b=int(B[c,t]);ae.encode(b,z,o)
            for d,k in zip(counts,keys):
                z0,o0=d.get(k,(1,1));d[k]=(z0,o0+1) if b else (z0+1,o0)
    araw,nbits=ae.finish();az=a.m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    tag=16+afid;payload=struct.pack('<BBII',tag,am,int(nbits),len(astore))+astore
    return payload,{'family':'adaptive_'+fam,'experts':list(experts),'groups':sum(len(x) for x in counts),'arith_bytes':len(astore),'arith_bits':int(nbits),'stored':len(payload),'ones':int(B.sum())}

def decode_adaptive_mix(buf,off,known,bit,tag,shape):
    afid=tag-16;fam=a.ADAPT[afid]
    if fam not in MIXES:return OLD_DECODE(buf,off,known,bit,tag,shape)
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9
    astore=buf[off:off+alen];off+=alen;araw=a.m.D.decompress(astore) if am else astore
    experts=MIXES[fam];counts=[{} for _ in experts];ad=a.rr.ArithDecoder(araw,nbits);B=a.np.zeros(shape,a.np.uint8)
    for t in range(shape[1]):
        for c in range(shape[0]):
            keys=[a.akey(known,B,bit,c,t,e) for e in experts];z,o=mixed_freq(counts,keys);b=ad.decode(z,o);B[c,t]=b
            for d,k in zip(counts,keys):
                z0,o0=d.get(k,(1,1));d[k]=(z0,o0+1) if b else (z0+1,o0)
    return B,off

a.encode_adaptive=encode_adaptive_mix
a.decode_adaptive_payload=decode_adaptive_mix

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_context_mixture_address.json'
    d=json.load(open(src));d['order']=1;d['train']=64;d['adaptive_families']=list(a.ADAPT);d['mixtures']={k:list(v) for k,v in MIXES.items()}
    d['scope']='Exact AR1/train64/step267 hybrid address with fixed decoder-shared mixtures of causal probability experts. PR600 rich single-context candidates remain available unchanged. Additional mixture candidates average deterministic fixed-point probabilities from several independently updated decoder-known context models (global, temporal, channel, prefix and richer neighboring-prefix experts). Every expert begins from the same 1/1 prior and is updated only from already decoded bits, so neither expert probabilities nor mixture weights are transmitted. A plane stores only its one-byte family tag and physical arithmetic payload. Full K decode, causal AR1 replay and the unchanged source hard-error bound are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'mixture_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
