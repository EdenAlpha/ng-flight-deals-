import json, subprocess, os, math, numpy as np
meta=json.load(open('data/forge_subcube_meta.json'))
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape'])
eps=float(meta['eps_10pct_std']); raw=X.nbytes; N=X.shape[-1]
F=np.fft.rfft(X,axis=2); BIN=os.environ['HPEZ_BIN']

def z(a):
    return len(subprocess.run(['zstd','-q','-f','-19','-T0','-c'],input=np.ascontiguousarray(a).tobytes(),stdout=subprocess.PIPE,check=True).stdout)
def si(a):
    lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    return a.astype(np.int8) if lo>=-128 and hi<=127 else a.astype(np.int16) if lo>=-32768 and hi<=32767 else a.astype(np.int32)
def cert(M):
    Q=np.rint((X-M)/(2*eps)).astype(np.int16); R=M+Q.astype(np.float32)*(2*eps); m=Q!=0
    opts=[z(si(Q)),z(si(np.transpose(Q,(2,0,1))))]
    for A in [Q,np.transpose(Q,(2,0,1))]:
        mm=A!=0; vv=A[mm]
        opts.append(z(np.packbits(mm.ravel(),bitorder='little'))+(z(si(vv)) if vv.size else 0))
    E=np.diff(Q,axis=2,prepend=Q[:,:,:1]); opts += [z(si(E)),z(si(np.transpose(E,(2,0,1))))]
    return min(opts),float(m.mean()),float(np.max(np.abs(X-R)))
def bounds(lo,hi,J):
    e=np.linspace(lo,hi+1,J+1).round().astype(int)
    return [(int(e[j]),int(e[j+1]-1)) for j in range(J) if e[j] <= e[j+1]-1]
def make_controls(lo,hi,J):
    arr=[]; spec=[]
    for a,b in bounds(lo,hi,J):
        kc=(a+b)//2; half=max(kc-a,b-kc); nc=max(4,2*half+2)
        if nc%2: nc+=1
        G=np.zeros(X.shape[:2]+(nc,),np.complex64)
        for k in range(a,b+1):
            G[:,:,(k-kc)%nc]=(2*F[:,:,k]*(nc/N)).astype(np.complex64)
        E=np.fft.ifft(G,axis=2).astype(np.complex64)
        arr.extend([E.real.astype(np.float32),E.imag.astype(np.float32)])
        spec.append((a,b,kc,nc))
    C=np.concatenate(arr,axis=2).astype('<f4')
    return C,spec
def reconstruct(D,spec):
    M=np.zeros_like(X,dtype=np.float32); pos=0; n=np.arange(N)
    for a,b,kc,nc in spec:
        Er=D[:,:,pos:pos+nc]; pos+=nc
        Ei=D[:,:,pos:pos+nc]; pos+=nc
        E=Er.astype(np.float32)+1j*Ei.astype(np.float32)
        Gd=np.fft.fft(E,axis=2); GN=np.zeros(X.shape[:2]+(N,),np.complex64)
        for d in range(-nc//2,(nc+1)//2):
            GN[:,:,d%N]=Gd[:,:,d%nc]*(N/nc)
        env=np.fft.ifft(GN,axis=2)
        M += (env*np.exp(1j*2*np.pi*kc*n/N)).real.astype(np.float32)
    return M

rows=[]
configs=[(8,65,2),(8,65,3),(8,65,4),(8,65,8),(5,70,2),(5,70,4),(8,70,2),(8,70,4)]
for lo,hi,J in configs:
    C,spec=make_controls(lo,hi,J); T=C.shape[-1]; C.tofile('subcore.bin')
    for beta in [.125,.25,.5,1.0,2.0]:
        cb=f'sub_{lo}_{hi}_{J}_{beta}.hpez'; out=f'sub_{lo}_{hi}_{J}_{beta}.bin'; bound=beta*eps
        subprocess.run([BIN,'-f','-i','subcore.bin','-z',cb,'-3',str(T),'64','64','-M','ABS',str(bound),'-q','4'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([BIN,'-f','-z',cb,'-o',out,'-3',str(T),'64','64'],check=True,stdout=subprocess.DEVNULL)
        D=np.fromfile(out,'<f4').reshape(64,64,T); M=reconstruct(D,spec); cc,nz,me=cert(M); coreb=os.path.getsize(cb); total=coreb+cc+96
        r={'lo':lo,'hi':hi,'J':J,'T':T,'beta':beta,'bytes':total,'ratio':raw/total,'core_bytes':coreb,'cert_bytes':cc,'cert_nz':nz,'maxerr':me}
        rows.append(r); print('SUBHPEZ',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['bytes'])
open('forge_subband_hpez_results.json','w').write(json.dumps({'eps':eps,'raw':raw,'best':rows[:40]},indent=2))
print('BEST',json.dumps(rows[:20],indent=2),flush=True)
