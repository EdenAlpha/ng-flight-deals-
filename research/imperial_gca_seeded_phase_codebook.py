import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128; NT=30000; C0=512; STEP=267; RAD=133; INC=2468803; S=64
MASK=(1<<64)-1
CONFIGS=[
    (128,'binary',64),(256,'binary',64),(256,'binary',96),(256,'binary',133),
    (256,'ternary',96),(256,'uniform',133),(512,'binary',96),(512,'uniform',133)
]


def splitmix(x):
    x=(x ^ (x>>np.uint64(30))) * np.uint64(0xbf58476d1ce4e5b9)
    x=(x ^ (x>>np.uint64(27))) * np.uint64(0x94d049bb133111eb)
    return x ^ (x>>np.uint64(31))


def patterns(c,b,L,kind,A):
    ss=np.arange(S,dtype=np.uint64)[:,None]
    pp=np.arange(L,dtype=np.uint64)[None,:]
    salt=((c+1)*0x9e3779b97f4a7c15 ^ (b+1)*0xd1b54a32d192ed03 ^ L*0x94d049bb133111eb) & MASK
    x=ss*np.uint64(0x632be59bd9b4e019) + pp*np.uint64(0x9e3779b97f4a7c15) + np.uint64(salt)
    h=splitmix(x)
    if kind=='binary': return np.where((h & np.uint64(1))!=0,A,-A).astype(np.int16)
    if kind=='ternary':
        q=(h % np.uint64(3)).astype(np.int8)
        return np.where(q==0,-A,np.where(q==1,0,A)).astype(np.int16)
    if kind=='uniform': return ((h % np.uint64(267)).astype(np.int16)-RAD).astype(np.int16)
    raise ValueError(kind)


def cost_array(k):
    a=np.abs(np.asarray(k,dtype=np.int64)); out=np.ones(a.shape,dtype=np.float64); nz=a>0
    if np.any(nz): out[nz]+=2.0+2.0*np.floor(np.log2(a[nz]))
    return out


def search_cfg(N,B,kind,A,sampled=False,return_seeds=False):
    nb=(NT+B-1)//B
    seeds=np.zeros((C,nb),np.uint8) if return_seeds else None
    total=0.0; base=0.0; nseen=0; blocks=0
    cs=range(0,C,4) if sampled else range(C)
    for c in cs:
        bs=range(0,nb,4) if sampled else range(nb)
        for bi in bs:
            t0=bi*B;t1=min(NT,t0+B);v=N[c,t0:t1].astype(np.int64);L=t1-t0
            P=patterns(c,bi,L,kind,A).astype(np.int64)
            K=np.floor_divide(v[None,:]-P+RAD,STEP)
            costs=cost_array(K).sum(axis=1);j=int(np.argmin(costs))
            total+=float(costs[j]);base+=float(cost_array(np.floor_divide(v+RAD,STEP)).sum());nseen+=L;blocks+=1
            if return_seeds: seeds[c,bi]=j
    seed_bits=8.0*blocks
    return {'B':B,'kind':kind,'A':A,'samples':nseen,'blocks':blocks,'payload_proxy_bps':total/nseen,'charged_proxy_bps':(total+seed_bits)/nseen,'baseline_proxy_bps':base/nseen,'gain_proxy_bps':(base-total-seed_bits)/nseen},seeds


def phase_from_seeds(B,kind,A,seeds):
    nb=seeds.shape[1];D=np.zeros((C,NT),np.int16)
    for c in range(C):
        for bi in range(nb):
            t0=bi*B;t1=min(NT,t0+B);L=t1-t0;P=patterns(c,bi,L,kind,A);D[c,t0:t1]=P[int(seeds[c,bi])]
    return D


def serialize_side(B,kind,A,seeds):
    kid={'binary':0,'ternary':1,'uniform':2}[kind]
    return struct.pack('<HBB',B,kid,A if kind!='uniform' else 0)+np.asarray(seeds,dtype=np.uint8).tobytes()


def parse_side(bb):
    B,kid,A=struct.unpack_from('<HBB',bb,0);kind={0:'binary',1:'ternary',2:'uniform'}[kid];nb=(NT+B-1)//B
    seeds=np.frombuffer(bb[4:4+C*nb],dtype=np.uint8).copy().reshape(C,nb)
    return B,kind,(133 if kind=='uniform' else int(A)),seeds


def encode_fixed(K):
    stream=bytearray();entries={};chosen={}
    for comp in cg.COMPONENTS:
        gr,W=rc.CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W)
        stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb)
        chosen[comp]={'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb)}
    return bytes(stream),entries,chosen


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod)
    P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
    baseline=rc.k_proxy(K0);screens=[]
    for cfg in CONFIGS:
        r,_=search_cfg(N,*cfg,sampled=True,return_seeds=False);screens.append(r);print(json.dumps({'sample_screen':r}),flush=True)
    top=sorted(screens,key=lambda z:z['charged_proxy_bps'])[:2]
    full=[];seedsets={}
    for q in top:
        key=(q['B'],q['kind'],q['A']);r,seeds=search_cfg(N,*key,sampled=False,return_seeds=True);full.append(r);seedsets[key]=seeds;print(json.dumps({'full_screen':r}),flush=True)
    best=min(full,key=lambda z:z['charged_proxy_bps']);key=(best['B'],best['kind'],best['A']);seeds=seedsets[key]
    side=serialize_side(*key,seeds);B,kind,A,seeds2=parse_side(side);D=phase_from_seeds(B,kind,A,seeds2)
    # Important: now pay the recursive AR32 consequence of the high-dimensional legal phase field.
    R,K=rc.build_phase(X,cod,D);rec_proxy=rc.k_proxy(K)+8.0*len(side)/(C*NT)
    recursive={'B':B,'kind':kind,'A':A,'recursive_payload_proxy_bps':rc.k_proxy(K),'charged_recursive_proxy_bps':rec_proxy,'side_bytes':len(side),'maxerr':float(np.max(np.abs(X-R.astype(np.float64))))};print(json.dumps({'recursive':recursive}),flush=True)
    if rec_proxy>=baseline:
        out={'winner':'incumbent','bytes':INC,'eps':eps,'baseline_proxy_bps':baseline,'sample_screens':screens,'full_screens':full,'recursive':recursive,'scope':'NOVA seeded legal-world search. Public 64-seed phase libraries create a high-dimensional legal reconstruction per channel/time block; one seed byte per block is charged. Best candidate lost after exact recursive AR32 consequence, so no physical address was claimed.'};json.dump(out,open('imperial_gca_seeded_phase_codebook.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True);return
    stream,entries,chosen=encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=rc.decode_phase(Kd,cod,D)
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
    out={'winner':'seeded','B':B,'kind':kind,'A':A,'seeds':S,'bytes':int(total),'bps':8.0*total/(C*NT),'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'side_bytes':len(side),'component_stream_bytes':len(stream),'model_bytes':len(model),'maxerr':me,'eps':eps,'baseline_proxy_bps':baseline,'sample_screens':screens,'full_screens':full,'recursive':recursive,'chosen':chosen,'scope':'NOVA seeded legal-world codec. For each channel/time block, encoder searches 64 deterministic public phase patterns and transmits one seed byte. Decoder regenerates all sample-level residue classes from block coordinates and seed. Exact component arithmetic bytes, seed bytes, model and framing are charged; exact K and source reconstruction are independently replayed under unchanged hard error.'};json.dump(out,open('imperial_gca_seeded_phase_codebook.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
