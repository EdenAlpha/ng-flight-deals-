import json,sys,os,tempfile,subprocess,shutil
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGIONS=(('hard',512),('easy',2304));C=128;NT=4096;TRAIN=1024;TB=1024

def varint_pack(vals):
    x=np.asarray(vals,np.int64).ravel();u=((x<<1)^(x>>63)).astype(np.uint64)
    out=bytearray()
    for q in u:
        v=int(q)
        while v>=128:
            out.append((v&127)|128);v>>=7
        out.append(v)
    return bytes(out)

def varint_unpack(blob,n):
    vals=np.empty(n,np.uint64);j=0;v=0;shift=0
    for b in blob:
        v|=(b&127)<<shift
        if b&128:shift+=7
        else:
            if j>=n:raise RuntimeError('varint overflow')
            vals[j]=v;j+=1;v=0;shift=0
    if j!=n or shift!=0:raise RuntimeError(('varint count',j,n,shift))
    return ((vals>>1).astype(np.int64)^-(vals&1).astype(np.int64)).astype(np.int32)

def layout_bytes(K,name):
    if name.endswith('_time'):vals=K.T.ravel()
    else:vals=K.ravel()
    if name.startswith('varint'):return varint_pack(vals)
    if name.startswith('i16'):
        if int(K.min())<-32768 or int(K.max())>32767:return None
        return np.asarray(vals,dtype='<i2').tobytes()
    return np.asarray(vals,dtype='<i4').tobytes()

def parse_layout(blob,name,shape):
    n=shape[0]*shape[1]
    if name.startswith('varint'):v=varint_unpack(blob,n)
    elif name.startswith('i16'):v=np.frombuffer(blob,dtype='<i2').astype(np.int32)
    else:v=np.frombuffer(blob,dtype='<i4').astype(np.int32)
    if len(v)!=n:raise RuntimeError(('layout length',name,len(v),n))
    if name.endswith('_time'):return v.reshape(shape[1],shape[0]).T.copy()
    return v.reshape(shape).copy()

def ppmd_roundtrip(raw):
    td=tempfile.mkdtemp(prefix='ppmd-')
    try:
        ip=os.path.join(td,'k.bin');ap=os.path.join(td,'k.7z');od=os.path.join(td,'out')
        open(ip,'wb').write(raw)
        cmd=['7z','a','-bd','-y','-t7z',ap,ip,'-m0=PPMd','-mx=9']
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if p.returncode:raise RuntimeError(('7z encode',p.returncode,p.stdout[-2000:]))
        size=os.path.getsize(ap);os.makedirs(od,exist_ok=True)
        p=subprocess.run(['7z','x','-bd','-y',ap,'-o'+od],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if p.returncode:raise RuntimeError(('7z decode',p.returncode,p.stdout[-2000:]))
        dec=open(os.path.join(od,'k.bin'),'rb').read()
        if dec!=raw:raise RuntimeError('PPMd byte mismatch')
        return int(size),dec
    finally:shutil.rmtree(td,ignore_errors=True)

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    layouts=('i16_time','i16_channel','i32_time','i32_channel','varint_time','varint_channel')
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X);R,K=h.run_ar(X,co)
            base,_,_,Kd=h.arithmetic(K);Rd=h.decode_source(Kd,co)
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,'baseline',me,eps))
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            vv=[]
            for name in layouts:
                raw=layout_bytes(K,name)
                if raw is None:continue
                arc,dec=ppmd_roundtrip(raw);K2=parse_layout(dec,name,K.shape)
                if not np.array_equal(K2,K):raise RuntimeError((region,name,'K parse'))
                R2=h.decode_source(K2,co);me2=float(np.max(np.abs(X-R2.astype(np.float64))))
                if not np.array_equal(R2,R) or me2>eps*(1+1e-12):raise RuntimeError((region,name,'source decode',me2,eps))
                total=arc+h.MODEL_BYTES+16
                z={'layout':name,'raw_bytes':len(raw),'archive_bytes':arc,'bytes':int(total),'bps':8*total/X.size,'gain_vs_step267':float(base/total),'gain_vs_sz3':float(sz/total),'ratio_to_2x':float(total/(sz/2)),'maxerr':me2}
                vv.append(z);print(json.dumps({'region':region,'variant':z},indent=2),flush=True)
            best=min(vv,key=lambda z:z['bytes']);row={'region':region,'samples':int(X.size),'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'variants':vv};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Exact lossless backend gate on the unchanged Huber AR32 step267 K field. Six deterministic serializations are tested: int16/int32 time-major and channel-major plus zigzag unsigned LEB128 varints in both layouts. Each byte stream is compressed as a real 7z archive using the classical PPMd method, the actual archive bytes are charged together with the shared AR32 model and small outer framing, then the archive is extracted byte-for-byte, K is parsed exactly, the full recursive source is regenerated and the unchanged max-error contract is verified. No probability model or reconstruction side information is free. No AI. Draft/do not merge.'},open('imperial_ar32_ppmd_backend.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])