import json,sys,struct
import h5py,numpy as np
import imperial_fair_zsm_context_search as fz
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_decoder_phase_automaton as m

C=128;NT=30000;C0=512;TB=4096;STEP=267
MODEL_BYTES=177
OUTER_BYTES=34
FAIR_AR32=2469677
MATCHED_SZ3=2767977
GRAMMARS=('base','richmag','richall')
WINDOWS=(4,8,64)
MENU=tuple((g,w) for g in GRAMMARS for w in WINDOWS)


def physical_model_frame(co):
    raw=np.asarray(co,np.float32).tobytes()
    if len(raw)>MODEL_BYTES:raise RuntimeError(('model overflow',len(raw)))
    frame=raw+bytes(MODEL_BYTES-len(raw))
    cod=np.frombuffer(frame[:len(raw)],np.float32).copy()
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('model replay')
    return frame,cod


def outer_header():
    h=struct.pack('<4sH',b'SZP1',TB)
    return h+bytes(OUTER_BYTES-len(h))


def main(path):
    with h5py.File(path,'r') as hf:
        ds=hf['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[:,C0:C0+C],np.float64).T
    if X.shape!=(C,NT):raise RuntimeError(('shape',X.shape))
    _,co=ah.fits(X);model,cod=physical_model_frame(co);R,K=ah.run_ar(X,cod)
    me0=float(np.max(np.abs(X-R.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('encode hard',me0,eps))
    stream=bytearray();blocks=[]
    for bi,t0 in enumerate(range(0,NT,TB)):
        t1=min(NT,t0+TB);Kb=np.ascontiguousarray(K[:,t0:t1]);rows=[];best=None
        for sid,(gr,W) in enumerate(MENU):
            bb,nb=fz.encode(Kb,W,Kb.shape[1],gr)
            row={'selector':sid,'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb)};rows.append(row)
            if best is None or len(bb)<best[2]:best=(sid,(gr,W),len(bb),int(nb),bb)
        sid,(gr,W),nbyte,nb,bb=best
        entry=struct.pack('<BQI',sid,nb,len(bb))+bb;stream.extend(entry)
        blocks.append({'block':bi,'t0':t0,'t1':t1,'selector':sid,'grammar':gr,'W':W,'payload_bytes':nbyte,'entry_bytes':len(entry),'bits':nb,'candidates':rows})
        print(json.dumps({'block':bi,'t0':t0,'t1':t1,'winner':gr,'W':W,'payload_bytes':nbyte,'entry_bytes':len(entry)}),flush=True)
    outer=outer_header();container=outer+model+bytes(stream)
    if len(container)<OUTER_BYTES+MODEL_BYTES:raise RuntimeError('container short')
    magic,tb=struct.unpack_from('<4sH',container,0)
    if magic!=b'SZP1' or tb!=TB:raise RuntimeError(('outer replay',magic,tb))
    cod2=np.frombuffer(container[OUTER_BYTES:OUTER_BYTES+132],np.float32).copy()
    if not np.array_equal(cod2.view(np.uint32),cod.view(np.uint32)):raise RuntimeError('container model replay')
    off=OUTER_BYTES+MODEL_BYTES;Kd=np.empty_like(K)
    for bi,t0 in enumerate(range(0,NT,TB)):
        t1=min(NT,t0+TB)
        sid,nb,L=struct.unpack_from('<BQI',container,off);off+=13
        if sid>=len(MENU):raise RuntimeError(('selector',sid))
        bb=container[off:off+L];off+=L
        if len(bb)!=L:raise RuntimeError(('payload eof',bi,L,len(bb)))
        gr,W=MENU[sid];Kb=fz.decode(bb,int(nb),W,(C,t1-t0),gr);Kd[:,t0:t1]=Kb
    if off!=len(container):raise RuntimeError(('trailing',off,len(container)))
    if not np.array_equal(Kd,K):raise RuntimeError('full K replay')
    Rd=ah.decode_source(Kd,cod2)
    if not np.array_equal(Rd,R):raise RuntimeError('full AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('decode hard',me,eps))
    total=len(container)
    out={'region':'hard_full','shape':[C,NT],'samples':C*NT,'global_std':std,'eps':eps,'generator':'audited_huber_ar32','order':32,'train':1024,'step':STEP,'address':'session_zsm_portfolio','time_block':TB,'num_blocks':len(blocks),'outer_bytes':OUTER_BYTES,'model_bytes':MODEL_BYTES,'payload_plus_session_headers_bytes':len(stream),'bytes':total,'bps':8*total/(C*NT),'maxerr':me,'fair_ar32_richmag_bytes':FAIR_AR32,'delta_vs_fair_ar32':total-FAIR_AR32,'gain_vs_fair_ar32':FAIR_AR32/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'blocks':blocks,'scope':'Full-hard decoder-real Session-Seeded context-configuration portfolio on the exact audited Huber AR32 trajectory. Time is divided into fixed 4096-sample sessions. For each session the encoder exhaustively evaluates the same fixed public fair ZSM menu used by PR610 (base/richmag/richall x W=4/8/64), then physically stores one selector byte, exact arithmetic bit count, payload length and the winning stream. Probability state resets at public session boundaries. No source-trained routing model or search path is transmitted. A literal outer header and conservative 177-byte float32 model frame are included. The entire concatenated container is parsed to EOF, every session K field is independently arithmetic-decoded, all 3.84M samples are causally AR32-replayed across session boundaries, and the unchanged global-epsilon hard bound is checked. Strict incumbent is PR610 at 2,469,677 B.'}
    json.dump(out,open('imperial_huber_ar32_session_zsm_portfolio.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':total,'fair_ar32':FAIR_AR32,'delta':total-FAIR_AR32,'gain_vs_fair':FAIR_AR32/total,'sz3':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'blocks':len(blocks),'maxerr':me}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
