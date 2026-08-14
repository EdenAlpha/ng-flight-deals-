import json,sys,struct
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MAX_DIAM=266;CELL=MAX_DIAM+1
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

@njit(cache=True)
def _solve_dp(cnt,max_count):
    n=len(cnt);pref=np.zeros(n+1,np.int64)
    for i in range(n):pref[i+1]=pref[i]+cnt[i]
    dp=np.empty(n+1,np.float64);prev=np.empty(n+1,np.int32);groups=np.empty(n+1,np.int32)
    dp[0]=0.0;prev[0]=-1;groups[0]=0
    for e in range(1,n+1):
        best=-1e300;bp=-1;bg=1<<30;s0=max(0,e-max_count)
        for s in range(s0,e):
            q=pref[e]-pref[s];add=0.0 if q<=1 else float(q)*np.log2(float(q));v=dp[s]+add;g=groups[s]+1
            if v>best+1e-12 or (abs(v-best)<=1e-12 and g<bg):best=v;bp=s;bg=g
        dp[e]=best;prev[e]=bp;groups[e]=bg
    return prev

def design_partition(E):
    v=np.rint(np.asarray(E,np.float64)).astype(np.int64).ravel();lo=int(min(int(v.min()),0));hi=int(max(int(v.max()),0));cnt=np.bincount((v-lo).astype(np.int64),minlength=hi-lo+1).astype(np.int64)
    prev=_solve_dp(cnt,CELL);ends=[];e=len(cnt)
    while e>0:
        s=int(prev[e]);ends.append((s,e));e=s
    ends.reverse();widths=np.asarray([e-s for s,e in ends],np.uint16)
    if np.any(widths<1) or np.any(widths>CELL):raise RuntimeError(('bad widths',widths.min(),widths.max()))
    his=lo+np.cumsum(widths,dtype=np.int64)-1
    centers=np.empty(len(widths),np.int64);cur=lo
    for i,w in enumerate(widths):
        hh=cur+int(w)-1;centers[i]=(cur+hh)//2;cur=hh+1
    zero=int(np.searchsorted(his,0,side='left'))
    raw=struct.pack('<ii',lo,len(widths))+widths.astype('<u2').tobytes();blob=Z.compress(raw)
    # Prove model serialization is sufficient to rebuild the exact partition.
    dec=ZD.decompress(blob);lo2,g=struct.unpack('<ii',dec[:8]);w2=np.frombuffer(dec[8:],'<u2',count=g).astype(np.uint16)
    if lo2!=lo or not np.array_equal(w2,widths):raise RuntimeError('partition model decode')
    return {'lo':lo,'widths':widths,'his':his,'centers':centers,'zero':zero,'model_bytes':len(blob)+16,'groups':len(widths),'blob_bytes':len(blob)}

def sid_center(e,p):
    e=int(e);lo=p['lo'];his=p['his'];G=p['groups']
    if e<lo:
        j=(lo-1-e)//CELL+1;sid=-j;hh=lo-1-(j-1)*CELL;ll=hh-MAX_DIAM;center=(ll+hh)//2
    elif e>int(his[-1]):
        j=(e-int(his[-1])-1)//CELL;sid=G+j;ll=int(his[-1])+1+j*CELL;hh=ll+MAX_DIAM;center=(ll+hh)//2
    else:
        sid=int(np.searchsorted(his,e,side='left'));center=int(p['centers'][sid])
    return sid-p['zero'],center

def center_from_symbol(s,p):
    sid=int(s)+p['zero'];lo=p['lo'];his=p['his'];G=p['groups']
    if sid<0:
        j=-sid;hh=lo-1-(j-1)*CELL;ll=hh-MAX_DIAM;return (ll+hh)//2
    if sid>=G:
        j=sid-G;ll=int(his[-1])+1+j*CELL;hh=ll+MAX_DIAM;return (ll+hh)//2
    return int(p['centers'][sid])

def run_quantizer(X,co,parts):
    R=np.zeros(X.shape,np.int32);S=np.zeros(X.shape,np.int32);E=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p0=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            e=int(X[c,t])-p0;part=parts[0] if len(parts)==1 else parts[t//TB];s,cen=sid_center(e,part);S[c,t]=s;E[c,t]=e;R[c,t]=p0+cen
    return R,S,E

def decode_quantizer(S,co,parts):
    R=np.zeros(S.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p0=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            part=parts[0] if len(parts)==1 else parts[t//TB];R[c,t]=p0+center_from_symbol(int(S[c,t]),part)
    return R

def model_bytes(parts):return sum(int(p['model_bytes']) for p in parts)+8*len(parts)+8

def compact(p):return {'groups':p['groups'],'lo':p['lo'],'hi':int(p['his'][-1]),'min_width':int(p['widths'].min()),'max_width':int(p['widths'].max()),'mean_width':float(p['widths'].mean()),'model_bytes':p['model_bytes'],'blob_bytes':p['blob_bytes']}

def evaluate(X,co,parts,label,eps):
    R,S,E=run_quantizer(X,co,parts);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((label,'hard',me,eps))
    ab,nbit,nb,Sd=h.arithmetic(S);Rd=decode_quantizer(Sd,co,parts)
    if not np.array_equal(Sd,S) or not np.array_equal(Rd,R):raise RuntimeError((label,'decode'))
    dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if dme>eps*(1+1e-12):raise RuntimeError((label,'decoded hard',dme,eps))
    mb=model_bytes(parts);total=int(ab)+mb+1
    return {'label':label,'bytes':total,'bps':8*total/X.size,'arithmetic_base_bytes':int(ab),'partition_model_bytes':mb,'selector_byte':1,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'symbol_min':int(S.min()),'symbol_max':int(S.max()),'zero_fraction':float(np.mean(S==0)),'symbol_h0_bps':float(_entropy(S)),'maxerr':dme,'parts':[compact(p) for p in parts]},E

def _entropy(A):
    _,n=np.unique(np.asarray(A).ravel(),return_counts=True);p=n/n.sum();return -(p*np.log2(p)).sum()

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,co=h.fits(XF)
            R0,K0=h.run_ar(XF,co);base,nbit,nb,Kd=h.arithmetic(K0);R0d=h.decode_source(Kd,co);bme=float(np.max(np.abs(XF-R0d.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))
            # Decoder-real residual against the baseline path supplies the first source-trained partition. The partition bytes are transmitted.
            E0=X.astype(np.int64)-(R0.astype(np.int64)-STEP*K0.astype(np.int64));p0=design_partition(E0);cands=[]
            r,E1=evaluate(X,co,[p0],'global_iter0',eps);cands.append(r)
            # Lloyd-like redesign from the actual residual field induced by each candidate reconstruction. Final model is always transmitted, so this is a valid source-trained codec rather than side information.
            for it in (1,2):
                pp=design_partition(E1);r,E1=evaluate(X,co,[pp],f'global_iter{it}',eps);cands.append(r)
            # Nonstationary version: one independently transmitted entropy-optimal partition per 1024-time slab, designed from baseline decoder-real residuals.
            tparts=[design_partition(E0[:,t0:t0+TB]) for t0 in range(0,NT,TB)];rt,_=evaluate(X,co,tparts,'time1024_from_baseline',eps);cands.append(rt)
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(bb)
            for r in cands:r.update({'gain_vs_step267_arithmetic':base/r['bytes'],'gain_vs_sz3':sz/r['bytes'],'ratio_to_2x_sz3_target':r['bytes']/(sz/2)})
            best=min(cands,key=lambda z:z['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_arithmetic_bytes':int(base),'step267_arithmetic_bps':8*base/X.size,'step267_arithmetic_bits':int(nbit),'step267_symbol_bits':int(nb),'step267_maxerr':bme,'best':best,'candidates':cands}
            rows.append(row);print(json.dumps({'region':region,'sz3_bps':row['sz3_bps'],'step267_bps':row['step267_arithmetic_bps'],'best':best},indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'max_cell_diameter':MAX_DIAM,'rows':rows,'scope':'Executable target-trained entropy-optimized nonuniform innovation-cell gate. One transmitted float32 prefix-only Huber AR32+intercept is shared exactly as in the incumbent. Unlike fixed step267, the prediction residual integer line is partitioned into contiguous cells of variable width, each with diameter <=266, so reconstruction at the integer midpoint is provably <=133 source units from any residual in that cell, strictly inside the unchanged epsilon. The partition is solved by exact dynamic programming to minimize empirical scalar entropy of the design residual field; its start and all widths are Zstd-compressed, transmitted, decoded and charged. Tail cells continue deterministically with width267. Candidate symbols are bin IDs relative to the zero-residual bin and are encoded/decoded by the same cold-start previous-time/current-left bit-context arithmetic engine as the incumbent; the full recursive source is regenerated and hard-error checked. Three global source-trained redesign iterations are tested (each final model is explicitly transmitted, so no hidden side information), plus an 8-part time1024 nonstationary model designed from the baseline decoder-real residual. Exact step267 arithmetic and matched SZ3 are rerun on identical 128x8192 hard/easy regions. This is a scalar innovation-cell test, not a vector-code impossibility proof. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_ar32_nonuniform_innovation_cells.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
