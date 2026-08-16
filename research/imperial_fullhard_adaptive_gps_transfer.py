import json,sys,struct
import h5py,numpy as np
import imperial_hard_adaptive_gps_plane_address as a
import imperial_decoder_phase_automaton as m

T0=0
C0=512
C=128
T=30000
P=12
STEP=267
GLOBAL_HEADER=32
SELECTOR=1
HIST_AR32=2478995
# Frozen from the independently decoded 128x1024 AR12 calibration winner in PR #598.
# family ids: local2=0, prefixnz_local3=4, c4_local2=5, highneigh_local2=7.
CAL_FAMILY={8:0,7:5,6:7,5:7,4:7,3:7,2:4,1:0,0:4}


def transfer_frame(K):
    A=np.asarray(K,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length())
    known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'AGT1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8)
        raw=m.Z.compress(np.packbits(B.ravel(),bitorder='little').tobytes())
        best=(bytes([0])+struct.pack('<I',len(raw))+raw,
              {'mode':'raw','family':'raw_zstd','stored':1+4+len(raw)})
        fid=CAL_FAMILY.get(bit)
        if fid is not None:
            p,d=a.encode_adaptive(B,known,bit,fid);entry=bytes([1])+p
            if len(entry)<len(best[0]):best=(entry,{'mode':'adaptive',**d,'stored':len(entry)})
        entry,d=best;out.extend(entry);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
        print(json.dumps({'encoded_bit':bit,**d}),flush=True)
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'AGT1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('transfer header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        mode=buf[off];off+=1
        if mode==0:
            L=struct.unpack_from('<I',buf,off)[0];off+=4;store=buf[off:off+L];off+=L
            raw=m.D.decompress(store);B=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:A.size].astype(np.uint8).reshape(A.shape)
        elif mode==1:
            fam,am,nbits,L=struct.unpack_from('<BBII',buf,off);tot=10+L;payload=buf[off:off+tot];off+=tot
            expected=CAL_FAMILY.get(bit)
            if expected is None or fam!=expected:raise RuntimeError(('family selector',bit,fam,expected))
            B=a.decode_adaptive(payload,uu,bit,A.shape)
        else:raise RuntimeError(('mode',mode))
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('transfer trailing',off,len(buf)))
    Kd=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Kd,A):raise RuntimeError('transfer K replay')
    return len(buf),Kd,detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[T0:T0+T,C0:C0+C],np.float64).T
    if X.shape!=(C,T):raise RuntimeError(('shape',X.shape))
    mb,coef,R,K,me=a.build(X,eps,P)
    payload,Kd,detail=transfer_frame(K)
    mer=a.replay(X,eps,P,coef,Kd,R)
    total=int(mb)+int(payload)+GLOBAL_HEADER+SELECTOR
    try:
        szb,ori=m.szrun(X,eps)
        sz={'bytes':int(szb),'orientation':ori,'gain':szb/total}
    except Exception as e:
        sz={'error':repr(e)}
    out={'region':'hard_full','shape':[C,T],'samples':int(C*T),'global_std':std,'eps':eps,'order':P,'train':a.TRAIN,'step':STEP,
         'model_bytes':int(mb),'payload_bytes':int(payload),'header_bytes':GLOBAL_HEADER,'selector_bytes':SELECTOR,'bytes':int(total),'bps':8*total/(C*T),'maxerr':mer,
         'historical_ar32_zsm_bytes':HIST_AR32,'delta_vs_historical_ar32':int(total-HIST_AR32),'gain_vs_historical_ar32':HIST_AR32/total,'sz3':sz,
         'calibrated_families':{str(k):a.ADAPT_FAMILIES[v] for k,v in CAL_FAMILY.items()},'detail':detail,
         'scope':'Full 128x30000 hard-Imperial decoder-real generalization test of the Adaptive-GPS address discovered on an independent 128x1024 calibration block. AR12/train256/step267 is fixed. Per zigzag-K bitplane, the causal adaptive family is frozen from PR598 calibration; the only full-object competition is against packed-bit Zstd fallback and the resulting one-byte mode is physically stored. No full-object context-family search, probability table, search trajectory or ideal rate is used. The literal K stream is parsed to EOF, K is recovered exactly, all 3.84M AR samples are causally replayed, and the unchanged global-epsilon hard bound is verified. Historical 2,478,995-byte Huber AR32+ZSM is the incumbent threshold.'}
    json.dump(out,open('imperial_fullhard_adaptive_gps_transfer.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':total,'payload':payload,'model':mb,'historical_ar32':HIST_AR32,'delta':total-HIST_AR32,'gain_vs_historical_ar32':HIST_AR32/total,'maxerr':mer,'sz3':sz}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
