import sys,json
import imperial_ar8_adaptive_context_address as a

a.P=4
BASE=tuple(a.ADAPT)
EXTRA=(
 'prefix_tc_t2','prefix_tc_c2','prefix_tc_diag','prefix_tc_t2c2','prefix_tc_t2diag',
 'prefix_tc_hpt','prefix_tc_hpc','prefix_tc_hptc','prefix_tc_t3','prefix_tc_c3',
 'prefix_tc_phase2','prefix_tc_phase4','prefix_t2_c4','prefix_t2_t8'
)
a.ADAPT=BASE+EXTRA
_old=a.akey

def rich_akey(known,B,bit,c,t,fam):
    if fam in BASE:return _old(known,B,bit,c,t,fam)
    prefix=int(known[c,t]>>(bit+1));nc,nt=B.shape
    pt=int(B[c,t-1]) if t>0 else 2;pc=int(B[c-1,t]) if c>0 else 2
    pt2=int(B[c,t-2]) if t>1 else 2;pc2=int(B[c-2,t]) if c>1 else 2
    pt3=int(B[c,t-3]) if t>2 else 2;pc3=int(B[c-3,t]) if c>2 else 2
    dg=int(B[c-1,t-1]) if c>0 and t>0 else 2
    hpt=int(known[c,t-1]>>(bit+1)) if t>0 else -1
    hpc=int(known[c-1,t]>>(bit+1)) if c>0 else -1
    if fam=='prefix_tc_t2':return (prefix,pt,pc,pt2)
    if fam=='prefix_tc_c2':return (prefix,pt,pc,pc2)
    if fam=='prefix_tc_diag':return (prefix,pt,pc,dg)
    if fam=='prefix_tc_t2c2':return (prefix,pt,pc,pt2,pc2)
    if fam=='prefix_tc_t2diag':return (prefix,pt,pc,pt2,dg)
    if fam=='prefix_tc_hpt':return (prefix,pt,pc,hpt)
    if fam=='prefix_tc_hpc':return (prefix,pt,pc,hpc)
    if fam=='prefix_tc_hptc':return (prefix,pt,pc,hpt,hpc)
    if fam=='prefix_tc_t3':return (prefix,pt,pc,pt2,pt3)
    if fam=='prefix_tc_c3':return (prefix,pt,pc,pc2,pc3)
    if fam=='prefix_tc_phase2':return (prefix,pt,pc,t&1,c&1)
    if fam=='prefix_tc_phase4':return (prefix,pt,pc,t&3,c&3)
    if fam=='prefix_t2_c4':return (prefix,pt,pt2,c*4//nc)
    if fam=='prefix_t2_t8':return (prefix,pt,pt2,t*8//nt)
    raise ValueError(fam)

a.akey=rich_akey

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar4_rich_adaptive_context_address.json'
    d=json.load(open(src));d['adaptive_families']=list(a.ADAPT)
    d['scope']='Exact AR4/step267 hybrid restricted address with an expanded decoder-shared causal context grammar. In addition to PR594 contexts, the encoder may select contexts containing second/third temporal or channel bits, diagonal same-plane state, neighboring higher-prefix state, and tiny public coordinate phases. Every context is computed solely from already decoded state; no context table or learned probabilities are transmitted. Each plane stores only its selected one-byte adaptive family tag and physical arithmetic payload. Existing exact combinatorial-rank candidates remain available as a floor. Full K decode, causal AR4 replay, and the unchanged source hard-error bound are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'rich_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
