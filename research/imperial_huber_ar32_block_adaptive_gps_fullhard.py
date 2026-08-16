import json,sys,struct
import h5py,numpy as np
import imperial_huber_ar32_adaptive_gps_fullhard as h
import imperial_hard_adaptive_gps_plane_address as a
import imperial_decoder_phase_automaton as m

TB=1024
SCREEN=256
MAGIC=b'BGP1'
FAIR_AR32=2469677
MATCHED_SZ3=2767977


def raw_entry(B):
    store=m.Z.compress(np.packbits(B.ravel(),bitorder='little').tobytes())
    return bytes([0])+struct.pack('<I',len(store))+store,{'mode':'raw','family':'raw_zstd','stored':5+len(store)}


def pick_mode(B,known,bit):
    # Encoder-only session search on an early slice. The winning public family id is stored in the full entry.
    ss=min(SCREEN,B.shape[1]);Bs=np.ascontiguousarray(B[:,:ss]);Ks=np.ascontiguousarray(known[:,:ss])
    r,_=raw_entry(Bs);best=('raw',None,len(r))
    for fam in range(len(a.ADAPT_FAMILIES)):
        p,_=a.encode_adaptive(Bs,Ks,bit,fam);n=1+len(p)
        if n<best[2]:best=('adaptive',fam,n)
    return best


def encode_block(K):
    A=np.asarray(K,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',MAGIC,A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);mode,fam,screen_bytes=pick_mode(B,known,bit)
        if mode=='raw':entry,d=raw_entry(B)
        else:
            p,d=a.encode_adaptive(B,known,bit,fam);entry=bytes([1])+p;d={'mode':'adaptive',**d,'stored':len(entry)}
        out.extend(entry);detail.append({'bit':bit,'screen_choice_bytes':int(screen_bytes),**d});known|=B.astype(np.uint64)<<bit
    return bytes(out),detail


def decode_block(buf,off):
    start=off;magic,nc,nt,nb=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=MAGIC:raise RuntimeError(('block magic',magic,start))
    uu=np.zeros((nc,nt),np.uint64)
    for bit in range(nb-1,-1,-1):
        mode=buf[off];off+=1
        if mode==0:
            L=struct.unpack_from('<I',buf,off)[0];off+=4;store=buf[off:off+L];off+=L
            raw=m.D.decompress(store);B=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:nc*nt].astype(np.uint8).reshape((nc,nt))
        elif mode==1:
            fam,am,nbits,L=struct.unpack_from('<BBII',buf,off);tot=10+L;payload=buf[off:off+tot];off+=tot
            B=a.decode_adaptive(payload,uu,bit,(nc,nt))
        else:raise RuntimeError(('block mode',mode))
        uu|=B.astype(np.uint64)<<bit
    return m.unzig(uu).astype(np.int32),off


def main(path):
    with h5py.File(path,'r') as hf:
        ds=hf['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[:,h.C0:h.C0+h.C],np.float64).T
    if X.shape!=(h.C,h.NT):raise RuntimeError(('shape',X.shape))
    co=h.huber_fit(X);model,cod=h.physical_model_frame(co);R,K=h.run_ar(X,cod)
    me0=float(np.max(np.abs(X-R.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('encode hard',me0,eps))
    container=bytearray();blocks=[]
    for bi,t0 in enumerate(range(0,h.NT,TB)):
        t1=min(h.NT,t0+TB);frame,detail=encode_block(np.ascontiguousarray(K[:,t0:t1]));container.extend(frame)
        row={'block':bi,'t0':t0,'t1':t1,'samples':h.C*(t1-t0),'bytes':len(frame),'detail':detail};blocks.append(row)
        print(json.dumps({'block':bi,'t0':t0,'t1':t1,'bytes':len(frame),'families':[x['family'] for x in detail]}),flush=True)
    # Parse the literal concatenated block stream to EOF and recover every innovation.
    Kd=np.empty_like(K);off=0
    for bi,t0 in enumerate(range(0,h.NT,TB)):
        t1=min(h.NT,t0+TB);kb,off2=decode_block(container,off)
        if kb.shape!=(h.C,t1-t0):raise RuntimeError(('block shape',bi,kb.shape,t1-t0))
        Kd[:,t0:t1]=kb;off=off2
    if off!=len(container):raise RuntimeError(('container trailing',off,len(container)))
    if not np.array_equal(Kd,K):raise RuntimeError('full K replay')
    Rd=h.decode_source(Kd,cod)
    if not np.array_equal(Rd,R):raise RuntimeError('full AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('decode hard',me,eps))
    total=h.OUTER_BYTES+len(model)+len(container)
    out={'region':'hard_full','shape':[h.C,h.NT],'samples':h.C*h.NT,'global_std':std,'eps':eps,
         'generator':'audited_huber_ar32','order':h.P,'train':h.TRAIN,'step':h.STEP,
         'address':'session_block_adaptive_gps','time_block':TB,'screen_time':SCREEN,'num_blocks':len(blocks),
         'outer_bytes':h.OUTER_BYTES,'model_bytes':len(model),'payload_bytes':len(container),'bytes':int(total),'bps':8*total/(h.C*h.NT),'maxerr':me,
         'fair_ar32_richmag_bytes':FAIR_AR32,'delta_vs_fair_ar32':int(total-FAIR_AR32),'gain_vs_fair_ar32':FAIR_AR32/total,
         'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'blocks':blocks,
         'scope':'Full-hard decoder-real session-seeded Adaptive-GPS address on the exact audited Huber AR32 trajectory. Unlike the failed one-grammar-for-30k transfer, time is partitioned into fixed 1024-sample sessions. Within each session and zigzag-K bitplane, the encoder spends computation screening the fixed public Adaptive-GPS family menu on the first 256 samples, then physically emits the selected family over the complete session; raw packed-Zstd remains a public fallback. The selected family id is embedded in each adaptive entry, adaptive state resets deterministically at session boundaries, and no probability table/search path is transmitted. All session frames are literally concatenated, parsed sequentially to EOF, all 3.84M K values are recovered exactly, the global AR32 reconstruction is causally replayed across session boundaries, and the unchanged global-epsilon hard bound is verified. Strict incumbent is PR610 2,469,677 B.'}
    json.dump(out,open('imperial_huber_ar32_block_adaptive_gps_fullhard.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':total,'payload':len(container),'model':len(model),'outer':h.OUTER_BYTES,'blocks':len(blocks),'fair_ar32':FAIR_AR32,'delta':total-FAIR_AR32,'gain_vs_fair':FAIR_AR32/total,'sz3':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'maxerr':me}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
