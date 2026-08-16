import sys,json
import imperial_ar4_rich_adaptive_context_address as rich

a=rich.a
a.P=1
a.TRAIN=64
BASE=tuple(a.ADAPT)
OLD_AKEY=a.akey
COARSE=[]
for s in (1,2,3,4):
    for kind in ('prefix','t','tc','tc_t2','tc_diag','tc_hpt','tc_hptc'):
        COARSE.append(f'cp{s}_{kind}')
a.ADAPT=BASE+tuple(COARSE)

def coarse_akey(known,B,bit,c,t,fam):
    if fam in BASE:return OLD_AKEY(known,B,bit,c,t,fam)
    p=fam.split('_',1);skip=int(p[0][2:]);kind=p[1];shift=bit+1+skip
    prefix=int(known[c,t]>>shift);pt=int(B[c,t-1]) if t>0 else 2;pc=int(B[c-1,t]) if c>0 else 2
    pt2=int(B[c,t-2]) if t>1 else 2;dg=int(B[c-1,t-1]) if c>0 and t>0 else 2
    hpt=int(known[c,t-1]>>shift) if t>0 else -1;hpc=int(known[c-1,t]>>shift) if c>0 else -1
    if kind=='prefix':return prefix
    if kind=='t':return (prefix,pt)
    if kind=='tc':return (prefix,pt,pc)
    if kind=='tc_t2':return (prefix,pt,pc,pt2)
    if kind=='tc_diag':return (prefix,pt,pc,dg)
    if kind=='tc_hpt':return (prefix,pt,pc,hpt)
    if kind=='tc_hptc':return (prefix,pt,pc,hpt,hpc)
    raise ValueError(fam)

a.akey=coarse_akey

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_coarse_prefix_address.json'
    d=json.load(open(src));d['order']=1;d['train']=64;d['adaptive_families']=list(a.ADAPT);d['coarse_prefix_families']=list(COARSE)
    d['scope']='Exact AR1/train64/step267 rich adaptive address with decoder-shared prefix coarsening. PR600 families remain unchanged as a strict floor. Additional public context families deliberately ignore the nearest 1..4 already decoded higher K bits before combining the remaining coarse prefix with causal same-plane time/channel, second-time, diagonal, and neighboring coarse-prefix state. The family tag fully specifies the ignored-bit count; no mask, table, probability or learned side model is transmitted. This directly tests the PR608 diagnosis that bit0 improved when bits1/2 were excluded from its prefix. Full K decode, causal AR1 replay and unchanged source hard-error validation are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'coarse_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
