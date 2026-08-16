import json,sys,struct
import h5py,numpy as np
import imperial_fair_zsm_context_search as fz
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_decoder_phase_automaton as m

C=128;NT=30000;C0=512;SCREEN=4096
GRAMMARS=('base','richmag','richall');WINDOWS=(4,8,64);COMPONENTS=('zero','sign','pref','suff')
MODEL_BYTES=177;OUTER_BYTES=34;FAIR_AR32=2469677;MATCHED_SZ3=2767977

def nctx(gr): return q.NCTX if gr=='base' else fz.layout(gr)[-1]

def cctx(gr,prev,left,diag,ac,comp,qmag=None,pos=None):
    kind={'zero':'zero','sign':'sign','pref':'pref','suff':'suff'}[comp]
    return fz.ctxs(gr,prev,left,diag,ac,qmag=qmag,pos=pos,kind=kind)

def encode_component(K,comp,W,nt,gr):
    E=q.AE(nctx(gr));ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(nt):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            ac=q.ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;diag=int(K[c-1,t-1]) if c and t else 0;k=int(K[c,t]);iz=(k==0)
            if comp=='zero':E.put(1 if iz else 0,cctx(gr,prev,left,diag,ac,comp))
            elif not iz:
                mag=abs(k);qq=mag.bit_length()-1
                if comp=='sign':E.put(1 if k<0 else 0,cctx(gr,prev,left,diag,ac,comp))
                elif comp=='pref':
                    for j in range(qq):E.put(0,cctx(gr,prev,left,diag,ac,comp,pos=j))
                    E.put(1,cctx(gr,prev,left,diag,ac,comp,pos=qq))
                elif comp=='suff':
                    rem=mag-(1<<qq)
                    for bp in range(qq-1,-1,-1):E.put((rem>>bp)&1,cctx(gr,prev,left,diag,ac,comp,qmag=qq,pos=qq-1-bp))
                else:raise ValueError(comp)
            old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
    return E.finish()

def choose(K,comp):
    rows=[]
    for gr in GRAMMARS:
        for W in WINDOWS:
            bb,nb=encode_component(K,comp,W,SCREEN,gr);r={'component':comp,'grammar':gr,'W':W,'prefix_bytes':len(bb),'prefix_bits':int(nb)};rows.append(r);print(json.dumps(r),flush=True)
    rows.sort(key=lambda r:r['prefix_bytes']);return rows[0],rows

def config_id(gr,W):return GRAMMARS.index(gr)*len(WINDOWS)+WINDOWS.index(W)
def config_from_id(i):return GRAMMARS[i//len(WINDOWS)],WINDOWS[i%len(WINDOWS)]

def decode_components(entries,shape):
    dec={};cfg={};rings={};sums={}
    for comp,(sid,nb,bb) in entries.items():
        gr,W=config_from_id(sid);cfg[comp]=(gr,W);dec[comp]=q.AD(bb,nb,nctx(gr));rings[comp]=np.zeros((C,W),np.int32);sums[comp]=np.zeros(C,np.int64)
    K=np.zeros(shape,np.int32)
    for t in range(shape[1]):
        for c in range(C):
            prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;diag=int(K[c-1,t-1]) if c and t else 0
            acs={}
            for comp in COMPONENTS:
                gr,W=cfg[comp];cnt=min(t,W);acs[comp]=q.ac_state(sums[comp][c],cnt)
            gr,_=cfg['zero'];iz=dec['zero'].get(cctx(gr,prev,left,diag,acs['zero'],'zero'))
            if iz:k=0
            else:
                gr,_=cfg['sign'];neg=dec['sign'].get(cctx(gr,prev,left,diag,acs['sign'],'sign'))
                qq=0;gr,_=cfg['pref']
                while True:
                    b=dec['pref'].get(cctx(gr,prev,left,diag,acs['pref'],'pref',pos=qq))
                    if b:break
                    qq+=1
                    if qq>30:raise RuntimeError(('gamma overflow',c,t))
                rem=0;gr,_=cfg['suff']
                for pos in range(qq):rem=(rem<<1)|dec['suff'].get(cctx(gr,prev,left,diag,acs['suff'],'suff',qmag=qq,pos=pos))
                mag=(1<<qq)+rem;k=-mag if neg else mag
            K[c,t]=k
            for comp in COMPONENTS:
                gr,W=cfg[comp];rp=t%W;old=int(rings[comp][c,rp]);new=abs(k);rings[comp][c,rp]=new;sums[comp][c]+=new-old
    return K

def model_frame(co):
    raw=np.asarray(co,np.float32).tobytes();frame=raw+bytes(MODEL_BYTES-len(raw));cod=np.frombuffer(frame[:len(raw)],np.float32).copy()
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('model replay')
    return frame,cod

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=model_frame(co);R,K=ah.run_ar(X,cod)
    me0=float(np.max(np.abs(X-R.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('encode hard',me0,eps))
    chosen={};screens={};stream=bytearray()
    for comp in COMPONENTS:
        best,rows=choose(K,comp);screens[comp]=rows;gr=best['grammar'];W=best['W'];bb,nb=encode_component(K,comp,W,NT,gr);sid=config_id(gr,W);chosen[comp]={'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb),'selector':sid};stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb)
    # Parse literal component container.
    off=0;entries={}
    for comp in COMPONENTS:
        sid,nb,L=struct.unpack_from('<BQI',stream,off);off+=13;bb=bytes(stream[off:off+L]);off+=L;entries[comp]=(sid,int(nb),bb)
    if off!=len(stream):raise RuntimeError(('trailing',off,len(stream)))
    Kd=decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=ah.decode_source(Kd,cod)
    if not np.array_equal(Rd,R):raise RuntimeError('AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('decode hard',me,eps))
    total=OUTER_BYTES+len(model)+len(stream)
    out={'region':'hard_full','shape':[C,NT],'samples':C*NT,'global_std':std,'eps':eps,'generator':'audited_huber_ar32','order':32,'train':1024,'step':267,'address':'componentwise_zsm_gps','outer_bytes':OUTER_BYTES,'model_bytes':len(model),'component_stream_bytes':len(stream),'bytes':total,'bps':8*total/(C*NT),'maxerr':me,'chosen':chosen,'screens':screens,'fair_ar32_richmag_bytes':FAIR_AR32,'delta_vs_fair_ar32':total-FAIR_AR32,'gain_vs_fair_ar32':FAIR_AR32/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'scope':'Decoder-real component-wise coordinate-system search on the exact audited full-hard Huber AR32 K field. PR610 forced zero/nonzero, sign, Elias-gamma prefix and gamma suffix events to share one grammar/window choice. Here each component independently prefix-screens the same fixed public grammar menu base/richmag/richall x W=4/8/64 on the first 4096 time samples, then emits one full arithmetic substream. Four physical selectors, bit counts and lengths are charged. The substreams are parsed independently but decoded jointly in causal sample order, recovering exact K; the physically serialized Huber model is decoded, all 3.84M source samples are replayed, and the unchanged global-epsilon hard bound is checked. Strict incumbent is PR610 2,469,677 B.'}
    json.dump(out,open('imperial_huber_ar32_component_zsm_gps.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':total,'fair_ar32':FAIR_AR32,'delta':total-FAIR_AR32,'gain_vs_fair':FAIR_AR32/total,'sz3':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'chosen':chosen,'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
