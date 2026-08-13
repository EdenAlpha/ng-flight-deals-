import json,sys,math,os,tempfile,subprocess,shutil
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32;STEP=267;TRAIN=1024;T=4096;C=128
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
m.STEP=STEP

def build_k(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);R=np.zeros(X.shape,np.int64);K=np.zeros(X.shape,np.int64)
    for c in range(C):
        for t in range(T):
            if t<P:p=0
            else:
                v=float(cd[-1])
                for j in range(P):v+=float(cd[j])*float(R[c,t-1-j])
                if not math.isfinite(v):raise RuntimeError('nonfinite')
                p=int(np.rint(v))
            k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError(('hard',c,t))
            K[c,t]=k;R[c,t]=y
    b,rep,kd=m.encode_k(K);kd=np.asarray(kd,np.int64).reshape(K.shape)
    if not np.array_equal(kd,K):raise RuntimeError('incumbent decode')
    return cd,int(mb),K,R,{'incumbent_k_bytes':int(b),'incumbent_rep':rep}

def zigzag(K):
    x=np.asarray(K,np.int64);return ((x<<1)^(x>>63)).astype(np.uint64)
def unzigzag(u):
    u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^(-((u&1).astype(np.int64))))

def ffmpeg_exists():return shutil.which('ffmpeg') is not None

def encode_plane(arr,codec,layout,tmp,tag):
    # arr is C x T uint8.
    if layout=='tile32':
        H=32;W=C;nframes=(T+H-1)//H;pad=nframes*H-T
        a=arr.T
        if pad:a=np.pad(a,((0,pad),(0,0)),mode='edge')
        raw=a.reshape(nframes,H,W).astype(np.uint8)
    elif layout=='strip16':
        H=16;W=C;nframes=T
        raw=np.repeat(arr.T[:,None,:],H,axis=1).astype(np.uint8);pad=0
    else:raise ValueError(layout)
    inp=os.path.join(tmp,tag+'.raw');out=os.path.join(tmp,tag+'.mkv');dec=os.path.join(tmp,tag+'.dec.raw')
    raw.tofile(inp)
    common=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','gray','-s:v',f'{W}x{H}','-framerate','500','-i',inp,'-an']
    if codec=='x264':
        cmd=common+['-c:v','libx264','-preset','slow','-qp','0','-x264-params',f'keyint={nframes}:min-keyint={nframes}:scenecut=0:ref=8:bframes=8','-pix_fmt','yuv444p','-f','matroska',out]
    elif codec=='ffv1':
        cmd=common+['-c:v','ffv1','-level','3','-coder','1','-context','1','-pix_fmt','gray','-f','matroska',out]
    else:raise ValueError(codec)
    try:subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
    except Exception as e:return {'ok':False,'error':repr(e),'codec':codec,'layout':layout}
    try:subprocess.run(['ffmpeg','-y','-v','error','-i',out,'-f','rawvideo','-pix_fmt','gray',dec],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
    except Exception as e:return {'ok':False,'error':'decode '+repr(e),'codec':codec,'layout':layout}
    got=np.fromfile(dec,np.uint8)
    if got.size!=raw.size:return {'ok':False,'error':f'decode size {got.size}!={raw.size}','codec':codec,'layout':layout}
    got=got.reshape(raw.shape)
    if not np.array_equal(got,raw):return {'ok':False,'error':'pixel mismatch','codec':codec,'layout':layout}
    if layout=='tile32':rec=got.reshape(-1,W)[:T].T.copy()
    else:
        if not np.all(got==got[:,0:1,:]):return {'ok':False,'error':'strip duplicate rows changed','codec':codec,'layout':layout}
        rec=got[:,0,:].T.copy()
    if not np.array_equal(rec,arr):return {'ok':False,'error':'logical plane mismatch','codec':codec,'layout':layout}
    return {'ok':True,'bytes':os.path.getsize(out),'codec':codec,'layout':layout,'frames':nframes,'width':W,'height':H,'reconstructed':rec}

def video_encode(K):
    u=zigzag(K);mx=int(u.max());nbytes=max(1,(mx.bit_length()+7)//8);planes=[((u>>(8*j))&255).astype(np.uint8) for j in range(nbytes)]
    definitions=(('x264','strip16'),('x264','tile32'),('ffv1','tile32'))
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        for codec,layout in definitions:
            total=48;recs=[];detail=[];ok=True
            for j,p in enumerate(planes):
                z=encode_plane(p,codec,layout,tmp,f'{codec}_{layout}_p{j}');detail.append({k:v for k,v in z.items() if k!='reconstructed'})
                if not z.get('ok'):ok=False;break
                total+=int(z['bytes']);recs.append(z['reconstructed'])
            if ok:
                uu=np.zeros(K.shape,np.uint64)
                for j,p in enumerate(recs):uu|=p.astype(np.uint64)<<(8*j)
                kd=unzigzag(uu)
                if not np.array_equal(kd,K):raise RuntimeError(('video K mismatch',codec,layout))
                rows.append({'codec':codec,'layout':layout,'bytes':int(total),'bps':8*total/K.size,'n_byteplanes':nbytes,'max_zigzag':mx,'details':detail,'K':kd})
            else:rows.append({'codec':codec,'layout':layout,'error':detail[-1].get('error'),'details':detail})
    return rows

def replay(K,co):
    R=np.zeros(K.shape,np.int64)
    for c in range(C):
        for t in range(T):
            if t<P:p=0
            else:
                v=float(co[-1])
                for j in range(P):v+=float(co[j])*float(R[c,t-1-j])
                p=int(np.rint(v))
            R[c,t]=p+STEP*int(K[c,t])
    return R

def main(path):
    if not ffmpeg_exists():raise RuntimeError('ffmpeg not installed')
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:T,c0:c0+C],np.float64).T;co,mb,K,R,base=build_k(X,eps);inc=mb+base['incumbent_k_bytes']+20
            vr=video_encode(K);cands=[]
            for z in vr:
                if 'bytes' not in z:continue
                RR=replay(z.pop('K'),co);me=float(np.max(np.abs(X-RR)))
                if me>eps*(1+1e-10):raise RuntimeError(('video hard',name,z['codec'],z['layout'],me,eps))
                z['model_bytes']=mb;z['total_bytes']=int(mb+z['bytes']);z['total_bps']=8*z['total_bytes']/K.size;z['maxerr']=me;z['gain_vs_incumbent']=inc/z['total_bytes'];cands.append(z)
            best=min(cands,key=lambda z:z['total_bytes']) if cands else None
            row={'region':name,'c0':c0,'model_bytes':mb,'incumbent_bytes':int(inc),'incumbent_bps':8*inc/K.size,'incumbent_rep':base['incumbent_rep'],'video_candidates':vr if False else cands,'best_video':best,
                 'best_gain_vs_incumbent':best['gain_vs_incumbent'] if best else None}
            rows.append(row);print(json.dumps(row,default=str),flush=True)
    inc=sum(x['incumbent_bytes'] for x in rows);best=sum(x['best_video']['total_bytes'] for x in rows if x['best_video']) if all(x['best_video'] for x in rows) else None;n=C*T*len(rows)
    out={'global_std':std,'eps':eps,'step':STEP,'ar_order':P,'shape':[C,T],'regions':[list(x) for x in SPECS],'rows':rows,
         'aggregate':{'incumbent_bytes':inc,'incumbent_bps':8*inc/n,'best_video_bytes':best,'best_video_bps':8*best/n if best else None,'gain_vs_incumbent':inc/best if best else None},
         'scope':'Cross-domain lossless-video backend gate on the exact persistent AR32 step267 innovation field. Signed K is zigzagged and split into exact 8-bit planes. Each plane is encoded either as H.264 lossless (libx264 qp=0) or FFV1. `strip16` makes each time sample one video frame with 16 identical rows so inter-frame motion/prediction runs directly along DAS time while preserving the 128-channel spatial row; `tile32` makes 32 consecutive times a 128x32 frame. Matroska container bytes are fully counted per plane. Every video is decoded to raw pixels, exact K is rebuilt, AR32 is replayed and unchanged hard error is verified. The incumbent uses the identical K field and current self-decoding Zstd menu. This is a backend/representation gate, not a whole-array claim; no AI.'}
    print(json.dumps(out['aggregate'],indent=2),flush=True);json.dump(out,open('imperial_ar32_lossless_video_backend.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
