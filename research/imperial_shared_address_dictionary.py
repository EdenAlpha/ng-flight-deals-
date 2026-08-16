import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar
import imperial_persistent_ar32_full_array_jit as inc

C=128; NT=4096; T0=14488; TRAIN=1024; P=32; TARGET_STEP=267
REGIONS=(('hard',512),('easy',2304)); DICT_SIZES=(8192,32768,65536,112640); HEADER=64

def bitplanes(K):
    x=np.asarray(K,np.int64);u=((x<<1)^(x>>63)).astype(np.uint64).ravel();w=max(1,int(int(u.max()).bit_length()))
    return b''.join(np.packbits(((u>>b)&1).astype(np.uint8),bitorder='little').tobytes() for b in range(w)),w,K.shape

def inv_bitplanes(raw,w,shape):
    n=int(np.prod(shape));pb=(n+7)//8;u=np.zeros(n,np.uint64);off=0
    for b in range(w):
        q=np.frombuffer(raw[off:off+pb],np.uint8);bits=np.unpackbits(q,bitorder='little')[:n].astype(np.uint64);u|=bits<<b;off+=pb
    return (((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)).reshape(shape)

def chunks(b,n=8192):
    return [b[i:i+n] for i in range(0,len(b),n) if len(b[i:i+n])>=256]

def get_address(path,region,c0,target=False):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+NT,c0:c0+C],np.float64).T
    step=TARGET_STEP if target else int(math.floor(2*eps));old=m.STEP;m.STEP=step
    try:
        co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=inc.build(X,cd)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('hard',path,region,step,me,eps))
        raw,w,shape=bitplanes(K)
        return {'std':std,'eps':eps,'step':step,'X':X,'K':np.asarray(K,np.int32),'cd':cd,'model_bytes':int(mb),'raw':raw,'width':w,'shape':shape,'maxerr':me}
    finally:m.STEP=old

def replay(rec,K):
    old=m.STEP;m.STEP=rec['step']
    try:R=inc.decode(np.asarray(K,np.int32),rec['cd'])
    finally:m.STEP=old
    me=float(np.max(np.abs(rec['X']-R.astype(np.float64))))
    if me>rec['eps']*(1+1e-12):raise RuntimeError(('replay',me,rec['eps']))
    return me

def main(p0,p1,pt):
    train=[];train_meta=[]
    for p in (p0,p1):
        for region,c0 in REGIONS:
            r=get_address(p,region,c0,False);train.extend(chunks(r['raw']));train_meta.append({'region':region,'std':r['std'],'step':r['step'],'bytes':len(r['raw']),'width':r['width']})
    dicts=[]
    for ds in DICT_SIZES:
        try:
            dd=zstd.train_dictionary(ds,train);dicts.append((ds,dd))
        except Exception as e:print('dict_skip',ds,repr(e),flush=True)
    if not dicts:raise RuntimeError('no dictionary trained')
    rows=[]
    for region,c0 in REGIONS:
        r=get_address(pt,region,c0,True);old=m.STEP;m.STEP=TARGET_STEP
        try:fr=m.encode_k(r['K'])
        finally:m.STEP=old
        if not np.array_equal(np.asarray(fr[2],np.int32),r['K']):raise RuntimeError('incumbent K')
        base=int(fr[0])+r['model_bytes']+HEADER
        nd=zstd.ZstdCompressor(level=19).compress(r['raw']);cands=[]
        for ds,dd in dicts:
            zc=zstd.ZstdCompressor(level=19,dict_data=dd);zd=zstd.ZstdDecompressor(dict_data=dd);blob=zc.compress(r['raw']);raw2=zd.decompress(blob)
            if raw2!=r['raw']:raise RuntimeError('dict bytes')
            K2=inv_bitplanes(raw2,r['width'],r['shape'])
            if not np.array_equal(K2,r['K']):raise RuntimeError('dict K')
            me=replay(r,K2);db=len(dd.as_bytes());shared=len(blob)+r['model_bytes']+HEADER;standalone=shared+db
            cands.append({'dict_nominal_bytes':ds,'dict_actual_bytes':db,'payload_bytes':len(blob),'shared_total_bytes':shared,'standalone_total_bytes':standalone,'shared_gain_vs_incumbent':base/shared,'standalone_gain_vs_incumbent':base/standalone,'maxerr':me})
        cands.sort(key=lambda x:x['shared_total_bytes']);best=cands[0]
        row={'region':region,'c0':c0,'samples':int(r['K'].size),'target_std':r['std'],'eps':r['eps'],'step':r['step'],'bitplane_width':r['width'],'incumbent':{'bytes':base,'innovation_bytes':int(fr[0]),'model_bytes':r['model_bytes'],'rep':fr[1],'bps':8*base/r['K'].size},'plain_zstd19_bitplanes_bytes':len(nd)+r['model_bytes']+HEADER,'best_shared_dictionary':best,'all_dictionaries':cands}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'training_records':[p0,p1],'target_record':pt,'training_meta':train_meta,'dictionary_sizes':list(DICT_SIZES),'rows':rows,'scope':'Exact decoder-real shared-model address-dictionary gate inspired by make_files.py. Two chronologically previous Imperial records only train one Zstd dictionary pool from hard+easy AR32 bitplane address chunks; target bytes never enter dictionary training. Target uses frozen step267 incumbent AR32. Dictionary-compressed target bitplanes are actually decompressed, inverted to exact K, AR32 replayed, and hard-error checked. shared_total_bytes treats the frozen dictionary as decoder-owned/amortized codec infrastructure; standalone_total_bytes charges the complete dictionary. Both are reported and must not be conflated. No ideal entropy or target-trained dictionary.'};json.dump(out,open('imperial_shared_address_dictionary.json','w'),indent=2)
if __name__=='__main__':main(*sys.argv[1:4])
