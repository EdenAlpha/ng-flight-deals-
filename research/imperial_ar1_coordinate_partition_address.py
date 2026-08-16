import sys,json
import imperial_ar1_coarse_prefix_address as cp

a=cp.a
BASE=tuple(a.ADAPT)
OLD_AKEY=a.akey

PART=[]
for k in (2,4,8,16,32,64):
    PART.append(f'coord_t{k}')
for k in (2,4,8,16,32):
    PART.append(f'coord_c{k}')
for kt,kc in ((2,2),(4,2),(4,4),(8,2),(8,4),(8,8),(16,2),(16,4),(16,8),(32,2),(32,4)):
    PART.append(f'coord_tc{kt}x{kc}')
for k in (8,16,32,64,128):
    PART.append(f'coord_scan{k}')
for k in (2,4,8):
    PART.append(f'phase_t{k}')
    PART.append(f'phase_c{k}')
    PART.append(f'phase_tc{k}')

a.ADAPT=BASE+tuple(PART)

def partition_akey(known,B,bit,c,t,fam):
    if fam in BASE:
        return OLD_AKEY(known,B,bit,c,t,fam)
    nc,nt=B.shape
    if fam.startswith('coord_t'):
        k=int(fam[7:]);return min(k-1,t*k//nt)
    if fam.startswith('coord_c'):
        k=int(fam[7:]);return min(k-1,c*k//nc)
    if fam.startswith('coord_tc'):
        q=fam[8:];kt,kc=(int(x) for x in q.split('x'))
        return (min(kt-1,t*kt//nt),min(kc-1,c*kc//nc))
    if fam.startswith('coord_scan'):
        k=int(fam[10:]);i=t*nc+c;n=nc*nt
        return min(k-1,i*k//n)
    if fam.startswith('phase_t'):
        k=int(fam[7:]);return t%k
    if fam.startswith('phase_c'):
        k=int(fam[7:]);return c%k
    if fam.startswith('phase_tc'):
        k=int(fam[8:]);return (t%k,c%k)
    raise ValueError(fam)

a.akey=partition_akey

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_coordinate_partition_address.json'
    d=json.load(open(src));d['order']=1;d['train']=64;d['adaptive_families']=list(a.ADAPT);d['coordinate_partition_families']=list(PART)
    d['scope']='Exact AR1/train64/step267 address with the proven rich/coarse-prefix families retained as a strict floor plus public decoder-shared coordinate partitions. The new families intentionally remove local/prefix state and allow only coarse time, channel, joint time-channel, linear-scan or periodic coordinate classes to carry separate adaptive probabilities. This directly tests whether stubborn low bitplanes 1/2 are globally coded only because useful nonstationarity is being destroyed by over-specific causal contexts. Every partition is fixed by its one-byte family tag; no boundaries, probabilities, reset points or target-trained side tables are transmitted. Full K decode, causal AR1 replay and unchanged source hard-error validation are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'partition_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
