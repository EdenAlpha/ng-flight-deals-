import json,math,struct,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133;INC=2468803;MATCHED_SZ3=2767977
PHASES=(-133,-96,-64,-32,0,32,64,96,133)

def clip4(k):return max(0,min(8,int(k)+4))
def onecost(k):
    a=abs(int(k))
    return 1.0 if a==0 else 3.0+2.0*math.floor(math.log2(a))

def fit_current_table(N,K0):
    G=np.clip(K0,-4,4).astype(np.int16)+4;tab=np.zeros(9,np.int16);rows=[]
    for g in range(9):
        v=N[G==g];best=(1e300,0)
        for d in PHASES:
            kk=np.floor_divide(v-int(d)+RAD,STEP);sc=rc.proxy_cost_k(kk)
            if sc<best[0]:best=(sc,d)
        tab[g]=best[1];rows.append({'kbin':g-4,'count':int(v.size),'phase':int(best[1]),'proxy_bits':float(best[0])})
    return tab,rows

def build(X,co,tab):
    Xi=np.rint(X).astype(np.int64);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);E=np.zeros(X.shape,np.uint8)
    a=float(co[0]);b=np.asarray(co[1:],np.float32);legal_multi=0
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            n=int(Xi[c,t])-p;k0=(n+RAD)//STEP;best=None;nlegal=0
            for k in range(k0-2,k0+3):
                d=int(tab[clip4(k)]);r=p+d+STEP*k;er=abs(int(Xi[c,t])-r)
                if er<=RAD:
                    nlegal+=1;key=(onecost(k),abs(k),er,k)
                    if best is None or key<best[0]:best=(key,k,r)
            if nlegal>1:legal_multi+=1
            if best is None:
                E[c,t]=1;k=k0;r=p+STEP*k
                if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('fallback illegal',c,t,n,k,r))
            else:_,k,r=best
            K[c,t]=int(k);R[c,t]=int(r)
    return R,K,E,legal_multi

def table_frame(tab):return b'SIC1'+np.asarray(tab,dtype='<i2').tobytes()
def parse_table(bb):
    if bb[:4]!=b'SIC1' or len(bb)!=22:raise RuntimeError('table frame')
    return np.frombuffer(bb[4:],dtype='<i2').copy()
def exception_frame(E):
    raw=np.packbits(E.reshape(-1),bitorder='big').tobytes();z=zstd.ZstdCompressor(level=19).compress(raw)
    mode=1 if len(z)<len(raw) else 0;store=z if mode else raw
    return struct.pack('<4sBII',b'EXC1',mode,E.size,len(store))+store

def parse_exception(bb,shape):
    magic,mode,n,L=struct.unpack_from('<4sBII',bb,0)
    if magic!=b'EXC1' or n!=int(np.prod(shape)) or len(bb)!=13+L:raise RuntimeError('exception frame')
    store=bb[13:];raw=zstd.ZstdDecompressor().decompress(store,max_output_size=(n+7)//8) if mode else store
    if len(raw)!=(n+7)//8:raise RuntimeError('exception raw')
    return np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='big')[:n].reshape(shape).astype(np.uint8)
def parse_k_stream(stream,shape):
    off=0;entries={}
    for comp in cg.COMPONENTS:
        sid,nb,L=struct.unpack_from('<BQI',stream,off);off+=13;payload=bytes(stream[off:off+L]);off+=L;entries[comp]=(int(sid),int(nb),payload)
    if off!=len(stream):raise RuntimeError(('K trailing',off,len(stream)))
    return cg.decode_components(entries,shape)
def decode(K,E,co,tab):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            k=int(K[c,t]);d=0 if E[c,t] else int(tab[clip4(k)]);R[c,t]=p+d+STEP*k
    return R

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-np.rint(X)))>1e-6:raise RuntimeError(('source setup',eps))
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
    tab,fit=fit_current_table(N,K0);R,K,E,multi=build(X,cod,tab);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('encode hard',me,eps))
    tf=table_frame(tab);ef=exception_frame(E);kstream,_,chosen=rc.encode_fixed(K)
    # Independent physical parse/decode of every transmitted object.
    tab2=parse_table(tf);E2=parse_exception(ef,K.shape);Kd=parse_k_stream(kstream,K.shape);cod2=np.frombuffer(model[:4*(ah.P+1)],dtype=np.float32).copy();Rd=decode(Kd,E2,cod2,tab2)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    if not np.array_equal(E2,E):raise RuntimeError('exception replay')
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('decode hard',mer,eps))
    total=cg.OUTER_BYTES+len(model)+len(tf)+len(ef)+len(kstream)
    out={'winner':'self_indexed_currentK','bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'eps':eps,'maxerr':mer,'step':STEP,'phase_table':[int(x) for x in tab],'table_frame_bytes':len(tf),'exception_frame_bytes':len(ef),'exception_count':int(E.sum()),'exception_fraction':float(E.mean()),'multi_legal_count':int(multi),'multi_legal_fraction':float(multi/E.size),'k_component_stream_bytes':len(kstream),'model_bytes':len(model),'outer_bytes':cg.OUTER_BYTES,'changed_k_vs_incumbent':int(np.sum(K!=K0)),'baseline_proxy_bps':rc.k_proxy(K0),'new_proxy_bps':rc.k_proxy(K),'fit_rows':fit,'chosen':chosen,'scope':'Exact self-indexed GCA codebook. The complete K address is decoded before source replay, so each transmitted K symbol selects its own public-table lattice phase. The encoder recursively enumerates nearby K symbols whose phase-conditioned center is inside the unchanged integer hard-error radius and greedily chooses the cheapest local magnitude symbol. If the learned self-indexed codebook has no legal center, a separately transmitted exception bit falls back to the guaranteed zero-phase step267 lattice. The 9-entry phase table, complete exception field, exact K component streams, AR32 model and framing are all physically serialized and charged. Decoder independently parses every object, recovers exact K/exception bits, regenerates all 3.84M samples and verifies the unchanged source hard-error bound.'};json.dump(out,open('imperial_gca_self_indexed_codebook.json','w'),indent=2);print(json.dumps({'summary':{k:v for k,v in out.items() if k not in ('fit_rows','chosen')}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
