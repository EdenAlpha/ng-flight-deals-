import sys,json,struct
import imperial_ar4_rich_adaptive_context_address as rich

a=rich.a
a.P=1
a.TRAIN=64
BASE=tuple(a.ADAPT)
OLD_ENCODE=a.encode_adaptive
OLD_DECODE=a.decode_adaptive_payload
FORGET={}
for th in (16,32,64,128,256,512,1024):FORGET[f'forget_global_{th}']=('global',th)
for base in ('prefix_t','prefix_tc'):
    for th in (32,64,128,256):FORGET[f'forget_{base}_{th}']=(base,th)
a.ADAPT=BASE+tuple(FORGET)

def shrink(z,o,th):
    if z+o<=th:return z,o
    return max(1,(z+1)//2),max(1,(o+1)//2)

def encode_forgetting(B,known,bit,afid):
    fam=a.ADAPT[afid]
    if fam not in FORGET:return OLD_ENCODE(B,known,bit,afid)
    base,th=FORGET[fam];counts={};ae=a.rr.ArithEncoder()
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            k=a.akey(known,B,bit,c,t,base);z,o=counts.get(k,(1,1));b=int(B[c,t]);ae.encode(b,z,o)
            if b:o+=1
            else:z+=1
            counts[k]=shrink(z,o,th)
    araw,nbits=ae.finish();az=a.m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    tag=16+afid;payload=struct.pack('<BBII',tag,am,int(nbits),len(astore))+astore
    return payload,{'family':'adaptive_'+fam,'base_family':base,'forget_threshold':th,'groups':len(counts),'arith_bytes':len(astore),'arith_bits':int(nbits),'stored':len(payload),'ones':int(B.sum())}

def decode_forgetting(buf,off,known,bit,tag,shape):
    afid=tag-16;fam=a.ADAPT[afid]
    if fam not in FORGET:return OLD_DECODE(buf,off,known,bit,tag,shape)
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9
    astore=buf[off:off+alen];off+=alen;araw=a.m.D.decompress(astore) if am else astore
    base,th=FORGET[fam];counts={};ad=a.rr.ArithDecoder(araw,nbits);B=a.np.zeros(shape,a.np.uint8)
    for t in range(shape[1]):
        for c in range(shape[0]):
            k=a.akey(known,B,bit,c,t,base);z,o=counts.get(k,(1,1));b=ad.decode(z,o);B[c,t]=b
            if b:o+=1
            else:z+=1
            counts[k]=shrink(z,o,th)
    return B,off

a.encode_adaptive=encode_forgetting
a.decode_adaptive_payload=decode_forgetting

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_forgetting_context_address.json'
    d=json.load(open(src));d['order']=1;d['train']=64;d['adaptive_families']=list(a.ADAPT);d['forgetting_families']={k:list(v) for k,v in FORGET.items()}
    d['scope']='Exact AR1/train64/step267 hybrid address with decoder-shared finite-memory probability states. PR600 rich contexts remain available unchanged. Additional candidates use the same causal context keys but deterministically halve Laplace counts whenever a public threshold is exceeded, allowing the probability model to track nonstationary bit statistics. Threshold and base context are completely determined by the one-byte family tag; no fitted probabilities, reset locations or side tables are transmitted. Encoder and decoder perform identical updates. Full K decode, causal AR1 replay and unchanged source hard-error validation are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'forget_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
