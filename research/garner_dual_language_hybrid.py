import json,math,os,sys,struct
import numpy as np,segyio,zstandard as zstd
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.garner_valley_das_full_benchmark import lattice_tile,encode_tile,sz3_best,SPACE,TIME,SAFETY

Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def main(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    if not np.all(np.isfinite(A)):raise RuntimeError('nonfinite')
    std=float(A.std(dtype=np.float64));eps=.1*std;internal=eps*SAFETY
    rows=[];selectors=[];payload_sum=0;sz3_sum=0;raw=A.nbytes;mx=0.;lat_count=spec_count=0
    for c0 in range(0,ntr,SPACE):
        c1=min(ntr,c0+SPACE)
        for t0 in range(0,ns,TIME):
            t1=min(ns,t0+TIME);W=np.ascontiguousarray(A[c0:c1,t0:t1]);AT=np.ascontiguousarray(W.T)
            sb,so,sme=sz3_best(AT,eps)
            lb,lme,lnz,lrep=lattice_tile(W,eps,internal)
            blob,pme,pd=encode_tile(W,internal);pb=len(blob)
            if not math.isfinite(pme) or pme>eps*(1+5e-6):raise RuntimeError(('spectral hard',pme,eps,c0,t0))
            if lb<=pb:
                sel=0;chosen=lb;lat_count+=1;chosen_me=lme
            else:
                sel=1;chosen=pb;spec_count+=1;chosen_me=pme
            selectors.append(sel);payload_sum+=chosen;sz3_sum+=sb;mx=max(mx,chosen_me)
            rows.append({'c0':c0,'t0':t0,'shape':list(W.shape),'selector':'lattice' if sel==0 else 'spectral','chosen_bytes':chosen,'lattice_bytes':lb,'spectral_bytes':pb,'sz3_bytes':sb,'gain_vs_sz3':sb/chosen,'lattice_transition_nonzero':lnz,'spectral_correction_nonzero':pd['correction_nonzero_fraction']})
    # Self-delimiting composition overhead. Method selectors are actually serialized; each tile gets an 8-byte payload length.
    bits=np.packbits(np.asarray(selectors,np.uint8),bitorder='little').tobytes();selector_blob=Z.compress(bits);decoded=np.unpackbits(np.frombuffer(D.decompress(selector_blob),np.uint8),bitorder='little',count=len(selectors)).astype(np.uint8)
    if not np.array_equal(decoded,np.asarray(selectors,np.uint8)):raise RuntimeError('selector roundtrip')
    directory_bytes=8*len(rows)
    fixed_header_bytes=128
    total=payload_sum+len(selector_blob)+directory_bytes+fixed_header_bytes
    # Hostile SZ3 baseline remains payload-only with zero metadata/directory.
    n=A.size
    out={'shape':[ntr,ns],'numeric_bytes':raw,'samples':n,'std':std,'eps':eps,'tiles':len(rows),'lattice_tiles':lat_count,'spectral_tiles':spec_count,
         'payload_bytes':payload_sum,'selector_bytes':len(selector_blob),'directory_bytes':directory_bytes,'fixed_header_bytes':fixed_header_bytes,'hybrid_bytes':total,
         'matched_sz3_payload_bytes':sz3_sum,'hybrid_ratio_raw':raw/total,'sz3_ratio_raw':raw/sz3_sum,'hybrid_bps':8*total/n,'sz3_bps':8*sz3_sum/n,'gain_vs_matched_sz3':sz3_sum/total,
         'maxerr':mx,'min_tile_gain':min(r['gain_vs_sz3'] for r in rows),'median_tile_gain':float(np.median([r['gain_vs_sz3'] for r in rows])),'max_tile_gain':max(r['gain_vs_sz3'] for r in rows),
         'rows':rows,'scope':'Real adaptive two-language Garner DAS composition. Every 128x1024 tile is independently encoded and hard-error decoded under the same global 10%-std epsilon by both our legal temporal lattice and frozen spectral/certified-correction grammar; encoder picks the smaller. Decoder receives an actually compressed one-bit method map plus an 8-byte payload length per tile and fixed 128-byte header. All selector/directory/header bytes are charged. Matched SZ3 gets identical tiling, best orientation per tile, and zero metadata, so the baseline is deliberately advantaged. No SZ3 payload is used inside the hybrid.'}
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open('garner_dual_language_hybrid.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
