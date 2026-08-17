import json,struct,sys,os
import numpy as np
import zstandard as zstd
import imperial_gca_state_residue_law as sl


def serialize_side(fam,tab):
    raw=np.asarray(tab,dtype='<i2').tobytes()
    comp=zstd.ZstdCompressor(level=19).compress(raw)
    if len(comp)<len(raw): mode=1;payload=comp
    else: mode=0;payload=raw
    return struct.pack('<BHB',sl.FAMILY_ID[fam],len(tab),mode)+payload


def parse_side(bb):
    fid,n,mode=struct.unpack_from('<BHB',bb,0);fam=sl.FAMILIES[fid];payload=bb[4:]
    raw=zstd.ZstdDecompressor().decompress(payload,max_output_size=2*n) if mode else payload
    if len(raw)!=2*n:raise RuntimeError(('table bytes',fam,len(raw),2*n))
    tab=np.frombuffer(raw,dtype='<i2').copy()
    if len(tab)!=sl.NCTX[fam]:raise RuntimeError(('table length',fam,len(tab)))
    return fam,tab


def main(path):
    sl.serialize_side=serialize_side;sl.parse_side=parse_side
    sl.main(path)
    d=json.load(open('imperial_gca_state_residue_law.json'))
    d['scope']=d['scope']+' Phase-table side information is now serialized as raw little-endian int16 or Zstd-19, whichever is physically smaller; the mode flag and table length are charged and the decoder reconstructs the exact table before source replay.'
    json.dump(d,open('imperial_gca_compressed_state_law.json','w'),indent=2)
    print(json.dumps({'compressed_state_summary':{'winner':d['winner'],'bytes':d['bytes'],'delta_vs_incumbent':d['delta_vs_incumbent'],'exact_candidates':d['exact_candidates']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
