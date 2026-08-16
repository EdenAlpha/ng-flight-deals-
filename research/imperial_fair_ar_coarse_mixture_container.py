import json,sys,struct
import h5py,numpy as np
import imperial_ar1_coarse_prefix_address as cp
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

# Install the proven PR623 mixture families on top of PR620 coarse-prefix contexts,
# then let every predictor candidate in the PR624 common container use the same address menu.
a=cp.a
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
 'mix_g_cp2':('global','cp2_tc_t2'),
 'mix_cp2_local':('cp2_tc','cp2_tc_t2','cp2_tc_diag'),
 'mix_g_cp2_local':('global','cp2_tc','cp2_tc_t2','cp2_tc_diag'),
}
a.ADAPT=BASE+tuple(MIXES)

def mixed_freq(counts,keys):
    ps=0
    for d,k in zip(counts,keys):
        z,o=d.get(k,(1,1));tot=z+o;p=(o*SCALE+tot//2)//tot
        if p<1:p=1
        elif p>=SCALE:p=SCALE-1
        ps+=p
    p=(ps+len(keys)//2)//len(keys)
    if p<1:p=1
    elif p>=SCALE:p=SCALE-1
    return SCALE-p,p

def encode_mix(B,known,bit,afid):
    fam=a.ADAPT[afid]
    if fam not in MIXES:return OLD_ENCODE(B,known,bit,afid)
    experts=MIXES[fam];counts=[{} for _ in experts];ae=a.rr.ArithEncoder()
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            keys=[a.akey(known,B,bit,c,t,e) for e in experts]
            z,o=mixed_freq(counts,keys);b=int(B[c,t]);ae.encode(b,z,o)
            for d,k in zip(counts,keys):
                z0,o0=d.get(k,(1,1));d[k]=(z0,o0+1) if b else (z0+1,o0)
    araw,nbits=ae.finish();az=a.m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    tag=16+afid;payload=struct.pack('<BBII',tag,am,int(nbits),len(astore))+astore
    return payload,{'family':'adaptive_'+fam,'experts':list(experts),'groups':sum(len(x) for x in counts),'arith_bytes':len(astore),'arith_bits':int(nbits),'stored':len(payload),'ones':int(B.sum())}

def decode_mix(buf,off,known,bit,tag,shape):
    afid=tag-16;fam=a.ADAPT[afid]
    if fam not in MIXES:return OLD_DECODE(buf,off,known,bit,tag,shape)
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9
    astore=buf[off:off+alen];off+=alen;araw=a.m.D.decompress(astore) if am else astore
    experts=MIXES[fam];counts=[{} for _ in experts];ad=a.rr.ArithDecoder(araw,nbits);B=a.np.zeros(shape,a.np.uint8)
    for t in range(shape[1]):
        for c in range(shape[0]):
            keys=[a.akey(known,B,bit,c,t,e) for e in experts]
            z,o=mixed_freq(counts,keys);b=ad.decode(z,o);B[c,t]=b
            for d,k in zip(counts,keys):
                z0,o0=d.get(k,(1,1));d[k]=(z0,o0+1) if b else (z0+1,o0)
    return B,off

a.encode_adaptive=encode_mix
a.decode_adaptive_payload=decode_mix
fair.A=a

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);rows=[]
    for cid,(p,scope) in enumerate(fair.CANDS):
        r=fair.one(X,eps,cid,p,scope);r['gain_vs_sz3']=szb/r['bytes'];rows.append(r)
        print(json.dumps({k:v for k,v in r.items() if k!='field_detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':fair.STEP,
         'candidates':[list(x) for x in fair.CANDS],'common_header_bytes':fair.COMMON_HEADER,
         'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,
         'mixtures':{k:list(v) for k,v in MIXES.items()},
         'scope':'Strict common-container composition of PR620 coarse-prefix contexts and PR623 decoder-shared probability mixtures. Every AR coordinate candidate receives the identical richer address menu, identical fixed 32-byte common header, one-byte candidate selector and compact reversible model serialization. No fitted mixture weights or probability tables are transmitted; mixture families and weights are public and selected only by their charged family tags. Every model/K field is independently decoded, causal reconstruction is replayed, and the unchanged source hard-error bound is checked.'}
    json.dump(out,open('imperial_fair_ar_coarse_mixture_container.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_scope':best['fit_scope'],
          'best_bytes':best['bytes'],'model_bytes':best['model_bytes'],'field_bytes':best['field_bytes'],
          'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
