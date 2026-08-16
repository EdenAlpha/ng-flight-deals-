import json,sys,struct
import h5py,numpy as np
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_decoder_phase_automaton as m

C=128;NT=30000;C0=512
TBS=(4096,8192)
SCREEN=512
NEW_INCUMBENT=2468803
MATCHED_SZ3=2767977
OUTER_BYTES=34
MODEL_BYTES=177


def choose_local(Kb,comp):
    n=min(SCREEN,Kb.shape[1]);rows=[]
    for gr in cg.GRAMMARS:
        for W in cg.WINDOWS:
            bb,nb=cg.encode_component(Kb,comp,W,n,gr);rows.append({'grammar':gr,'W':W,'prefix_bytes':len(bb),'prefix_bits':int(nb)})
    rows.sort(key=lambda r:r['prefix_bytes']);return rows[0],rows


def encode_tb(K,tb):
    stream=bytearray();blocks=[]
    for t0 in range(0,K.shape[1],tb):
        t1=min(K.shape[1],t0+tb);Kb=K[:,t0:t1];detail={}
        for comp in cg.COMPONENTS:
            best,screens=choose_local(Kb,comp);gr=best['grammar'];W=best['W'];bb,nb=cg.encode_component(Kb,comp,W,Kb.shape[1],gr);sid=cg.config_id(gr,W)
            stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb)
            detail[comp]={'grammar':gr,'W':W,'selector':sid,'bits':int(nb),'payload_bytes':len(bb),'screens':screens}
        blocks.append({'t0':t0,'t1':t1,'component_detail':detail})
        print(json.dumps({'tb':tb,'block':[t0,t1],'bytes_so_far':len(stream),'chosen':{k:{'grammar':v['grammar'],'W':v['W'],'payload_bytes':v['payload_bytes']} for k,v in detail.items()}},flush=True))
    return bytes(stream),blocks


def decode_tb(stream,tb,shape):
    off=0;parts=[]
    for t0 in range(0,shape[1],tb):
        t1=min(shape[1],t0+tb);entries={}
        for comp in cg.COMPONENTS:
            sid,nb,L=struct.unpack_from('<BQI',stream,off);off+=13;bb=bytes(stream[off:off+L]);off+=L;entries[comp]=(int(sid),int(nb),bb)
        parts.append(cg.decode_components(entries,(shape[0],t1-t0)))
    if off!=len(stream):raise RuntimeError(('trailing',off,len(stream)))
    return np.concatenate(parts,axis=1)


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R,K=ah.run_ar(X,cod);me0=float(np.max(np.abs(X-R.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('encode hard',me0,eps))
    rows=[]
    for sid,tb in enumerate(TBS):
        stream,blocks=encode_tb(K,tb);Kd=decode_tb(stream,tb,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',tb))
        Rd=ah.decode_source(Kd,cod)
        if not np.array_equal(Rd,R):raise RuntimeError(('R replay',tb))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('decode hard',tb,me,eps))
        total=OUTER_BYTES+MODEL_BYTES+1+len(stream)
        row={'tb':tb,'tb_selector':sid,'bytes':int(total),'component_stream_bytes':len(stream),'model_bytes':MODEL_BYTES,'outer_bytes':OUTER_BYTES,'selector_bytes':1,'blocks':len(blocks),'maxerr':me,'detail':blocks,'gain_vs_new_incumbent':NEW_INCUMBENT/total,'gain_vs_sz3':MATCHED_SZ3/total}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard_full','shape':[C,NT],'samples':C*NT,'global_std':std,'eps':eps,'generator':'audited_huber_ar32','order':32,'train':1024,'step':267,
         'address':'componentwise_session_zsm_gps','session_sizes':list(TBS),'screen':SCREEN,'rows':rows,'best':best,'previous_componentwise_incumbent':NEW_INCUMBENT,'matched_sz3_bytes':MATCHED_SZ3,
         'scope':'Composition of component-wise Adaptive-GPS and Session-Seeded-GPS on the exact audited Huber AR32 full-hard K trajectory. Fixed public sessions of 4096 or 8192 samples reset only entropy-model state; AR32 source reconstruction remains continuous across all 30,000 times. Inside each session, zero/nonzero, sign, gamma-prefix and gamma-suffix independently prefix-screen the fixed base/richmag/richall x W=4/8/64 menu and physically emit their chosen substream with selector, bit count and length. A one-byte public TB selector is charged. All session component streams are parsed and decoded to exact K, the serialized Huber model is replayed over all 3.84M samples, and unchanged hard error is checked. Strict target is PR631 2,468,803 B.'}
    json.dump(out,open('imperial_huber_component_session_zsm.json','w'),indent=2)
    print(json.dumps({'summary':{'previous':NEW_INCUMBENT,'best':best['bytes'],'delta':best['bytes']-NEW_INCUMBENT,'tb':best['tb'],'blocks':best['blocks'],'sz3':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best['bytes'],'maxerr':best['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
