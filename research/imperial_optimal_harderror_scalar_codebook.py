import heapq,json,math,sys
import h5py,numpy as np


def entropy(c):
    c=np.asarray(c,np.int64);c=c[c>0];n=int(c.sum());p=c/n
    return float(-(p*np.log2(p)).sum())

def huffman_bps(c):
    h=[int(x) for x in c if x>0];n=sum(h)
    if len(h)<=1:return 0.0
    heapq.heapify(h);cost=0
    while len(h)>1:
        a=heapq.heappop(h);b=heapq.heappop(h);s=a+b;cost+=s;heapq.heappush(h,s)
    return cost/n

def optimal_partition(counts,eps):
    vals=np.flatnonzero(counts).astype(np.int32)-32768
    c=counts[counts>0].astype(np.int64);m=len(vals);pref=np.zeros(m+1,np.int64);pref[1:]=np.cumsum(c)
    dp=np.full(m+1,-np.inf,np.float64);prev=np.full(m+1,-1,np.int32);dp[0]=0.0
    width=2.0*float(eps)
    for end in range(m):
        lo=int(np.searchsorted(vals,vals[end]-width-1e-12,side='left'))
        starts=np.arange(lo,end+1,dtype=np.int32)
        n=(pref[end+1]-pref[starts]).astype(np.float64)
        score=dp[starts]+n*np.log2(n)
        j=int(np.argmax(score));dp[end+1]=score[j];prev[end+1]=int(starts[j])
    groups=[];e=m
    while e>0:
        s=int(prev[e]);n=int(pref[e]-pref[s]);v0=int(vals[s]);v1=int(vals[e-1]);center=(v0+v1)/2.0
        groups.append({'lo':v0,'hi':v1,'count':n,'center':center,'maxerr':max(abs(center-v0),abs(center-v1))});e=s
    groups.reverse();gc=np.array([g['count'] for g in groups],np.int64);N=int(gc.sum())
    H=math.log2(N)-float(dp[m])/N if N else 0.0
    return {'entropy_bps':H,'huffman_bps':huffman_bps(gc),'groups':groups,'group_counts':gc.tolist(),'num_groups':len(groups),'max_group_error':max((g['maxerr'] for g in groups),default=0.0)}

def hist_dataset(d):
    counts=np.zeros(65536,np.int64);s=ss=0.0;n=0
    for t in range(0,d.shape[0],2048):
        x=np.asarray(d[t:min(t+2048,d.shape[0])],np.int16);u=x.astype(np.int32)+32768;counts+=np.bincount(u.ravel(),minlength=65536);z=x.astype(np.float64);s+=float(z.sum());ss+=float((z*z).sum());n+=x.size
    mu=s/n;std=float(np.sqrt(max(0,ss/n-mu*mu)));return counts,mu,std

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];counts,mu,std=hist_dataset(d);eps=.1*std;N=int(counts.sum())
        opt=optimal_partition(counts,eps)
        model_bytes=opt['num_groups']*8+32
        lower_bytes=math.ceil(N*opt['entropy_bps']/8)+model_bytes
        huff_bytes=math.ceil(N*opt['huffman_bps']/8)+model_bytes
        # 25 deterministic local oracles: how much nonstationarity could help if codebooks were region-specific.
        ts=np.linspace(0,d.shape[0]-1024,5,dtype=int);cs=np.linspace(0,d.shape[1]-128,5,dtype=int);tiles=[]
        for t0 in ts:
          for c0 in cs:
            x=np.asarray(d[t0:t0+1024,c0:c0+128],np.int16);hc=np.bincount((x.astype(np.int32)+32768).ravel(),minlength=65536);o=optimal_partition(hc,eps)
            tiles.append({'t0':int(t0),'c0':int(c0),'entropy_bps':o['entropy_bps'],'huffman_bps':o['huffman_bps'],'num_groups':o['num_groups'],'local_std':float(x.std(dtype=np.float64))})
        # Fixed 2eps lattice H0 control with a dense phase sweep over one period.
        step=2*eps;sample_vals=np.repeat(np.arange(-32768,32768,dtype=np.int32),np.minimum(counts,2000).astype(np.int32))
        # Weighted exact phase entropy from histogram; 128 deterministic phases.
        phases=np.linspace(0,step,128,endpoint=False);best=(1e9,None)
        v=np.arange(-32768,32768,dtype=np.float64);nz=counts>0;v=v[nz];w=counts[nz]
        for ph in phases:
            q=np.rint((v-ph)/step).astype(np.int32);_,inv=np.unique(q,return_inverse=True);cc=np.bincount(inv,weights=w).astype(np.int64);H=entropy(cc)
            if H<best[0]:best=(H,float(ph))
        target=3.7718057520037718/2.0
        out={'shape':list(d.shape),'dtype':str(d.dtype),'samples':N,'mean':mu,'std':std,'public_eps':eps,'max_cell_width':2*eps,'optimal_nonuniform_zero_order_entropy_bps':opt['entropy_bps'],'optimal_nonuniform_huffman_bps':opt['huffman_bps'],'num_codewords':opt['num_groups'],'max_codeword_error':opt['max_group_error'],'model_bytes_estimate':model_bytes,'entropy_lower_bound_container_bytes_estimate':lower_bytes,'huffman_container_bytes_estimate':huff_bytes,'native_bytes':N*2,'entropy_lower_bound_native_ratio':(N*2)/lower_bytes,'huffman_native_ratio':(N*2)/huff_bytes,'best_128phase_uniform_H0_bps':best[0],'best_uniform_phase':best[1],'verified_sz3_bps_reference':3.7718057520037718,'two_x_sz3_target_bps':target,'headroom_to_two_x_target_bps':target-opt['entropy_bps'],'tile_oracles':tiles,'median_tile_optimal_entropy_bps':float(np.median([r['entropy_bps'] for r in tiles])),'min_tile_optimal_entropy_bps':float(np.min([r['entropy_bps'] for r in tiles])),'max_tile_optimal_entropy_bps':float(np.max([r['entropy_bps'] for r in tiles])),'scope':'Exact dynamic program for the empirical zero-order entropy-minimizing nonuniform scalar reconstruction codebook under the unchanged hard max-error. Entropy result is a scalar-memoryless lower bound/ideal arithmetic rate, not a vector-code impossibility proof.'}
        print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_optimal_harderror_scalar_codebook.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
