import json,sys,math,struct
import h5py,numpy as np
import imperial_causal_restricted_address as ca
import imperial_address_aware_legal_search as a
import imperial_address_aware_pair_search as p
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_defect_restricted_rank_address as rr

VERSION=1
K=g.NTAPS
OFFS=g.candidate_offsets()
NGRAM=len(OFFS)
SET_BYTES=(math.comb(NGRAM,K).bit_length()+7)//8


def put_uvar(out,x):
    x=int(x)
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)

def get_uvar(buf,pos):
    x=0;s=0
    while True:
        if pos>=len(buf):raise RuntimeError('uvar eof')
        b=buf[pos];pos+=1;x|=(b&127)<<s
        if b<128:return x,pos
        s+=7

def zz(v):return 2*int(v) if int(v)>=0 else -2*int(v)-1
def unzz(u):return int(u)//2 if (int(u)&1)==0 else -(int(u)//2)-1

def put_svar(out,x):put_uvar(out,zz(x))
def get_svar(buf,pos):
    u,pos=get_uvar(buf,pos);return unzz(u),pos


def rank_combination(vals,n,k):
    vals=list(map(int,vals));r=0;prev=-1
    for i,x in enumerate(vals):
        for v in range(prev+1,x):r+=math.comb(n-v-1,k-i-1)
        prev=x
    return r

def unrank_combination(rank,n,k):
    r=int(rank);out=[];prev=-1
    for i in range(k):
        for v in range(prev+1,n):
            cnt=math.comb(n-v-1,k-i-1) if k-i-1>=0 else 1
            if r<cnt:
                out.append(v);prev=v;break
            r-=cnt
        else:raise RuntimeError('comb unrank')
    if r!=0:raise RuntimeError(('comb remainder',r))
    return out


def compact_model(dts,dcs,co,intercept):
    lut={tuple(x):i for i,x in enumerate(OFFS)}
    ids=[lut[(int(dt),int(dc))] for dt,dc in zip(dts,dcs)]
    if len(set(ids))!=K:raise RuntimeError('duplicate model tap')
    order=np.argsort(np.asarray(ids));sid=[ids[int(i)] for i in order];sco=[int(co[int(i)]) for i in order]
    rank=rank_combination(sid,NGRAM,K);raw=bytearray(rank.to_bytes(SET_BYTES,'little'))
    for q in sco:put_svar(raw,q)
    put_svar(raw,int(intercept))
    buf=bytes(raw);p0=0;rank2=int.from_bytes(buf[p0:p0+SET_BYTES],'little');p0+=SET_BYTES
    ids2=unrank_combination(rank2,NGRAM,K);co2=[]
    for _ in range(K):q,p0=get_svar(buf,p0);co2.append(q)
    inter2,p0=get_svar(buf,p0)
    if p0!=len(buf):raise RuntimeError('model trailing')
    ddt=np.asarray([OFFS[i][0] for i in ids2],np.int16);ddc=np.asarray([OFFS[i][1] for i in ids2],np.int16);cco=np.asarray(co2,np.int32)
    if ids2!=sid or co2!=sco or inter2!=int(intercept):raise RuntimeError('compact model replay')
    return buf,ddt,ddc,cco,int(inter2),{'grammar_size':NGRAM,'ntaps':K,'tapset_rank_bytes':SET_BYTES,'coef_varint_bytes':len(buf)-SET_BYTES-put_svar_len(intercept),'intercept_varint_bytes':put_svar_len(intercept),'total_bytes':len(buf)}

def put_svar_len(x):
    u=zz(x);n=1
    while u>=128:n+=1;u>>=7
    return n


def compact_defect(D):
    A=np.asarray(D,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());out=bytearray([nb]);detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for mode in ca.MODES:
            for order in ca.ORDERS:
                old,d=ca.encode_adaptive_plane(B,np.asarray(u & ~((np.uint64(1)<<(bit+1))-1),np.uint64),bit,mode,order)
                mi,oi,nbits,L=struct.unpack_from('<BBII',old,0);cm=int(old[10]);store=old[11:11+L]
                if len(store)!=L or 11+L!=len(old):raise RuntimeError('old causal parse')
                rem=int(nbits)&7;meta=(int(mi)&7)|((int(oi)&1)<<3)|((cm&1)<<4)|((rem&7)<<5)
                tmp=bytearray([meta]);put_uvar(tmp,L);tmp.extend(store);cand=bytes(tmp)
                if best is None or len(cand)<len(best[0]):best=(cand,{'bit':bit,'mode':mode,'order':order,'arith_bits':int(nbits),'payload_bytes':L,'compressed':bool(cm),'compact_bytes':len(cand),'ones':int(B.sum())})
        payload,det=best;out.extend(payload);detail.append(det)
    return bytes(out),detail


def decode_compact_defect(buf,pos,shape):
    if pos>=len(buf):raise RuntimeError('defect eof')
    nb=int(buf[pos]);pos+=1;uu=np.zeros(shape,np.uint64)
    for bit in range(nb-1,-1,-1):
        meta=int(buf[pos]);pos+=1;mi=meta&7;oi=(meta>>3)&1;cm=(meta>>4)&1;rem=(meta>>5)&7
        if mi>=len(ca.MODES) or oi>=len(ca.ORDERS):raise RuntimeError('compact selector')
        L,pos=get_uvar(buf,pos);store=buf[pos:pos+L];pos+=L
        if len(store)!=L:raise RuntimeError('compact payload eof')
        raw=m.D.decompress(store) if cm else bytes(store)
        if not raw:raise RuntimeError('empty arithmetic payload')
        nbits=len(raw)*8 if rem==0 else (len(raw)-1)*8+rem
        mode=ca.MODES[mi];order=ca.ORDERS[oi];cur=np.zeros(shape,np.uint8)
        _,nctx=ca.ctx_id(uu,cur,0,0,bit,mode);z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ad=rr.ArithDecoder(raw,nbits)
        for c0,t0 in ca.iter_coords(shape,order):
            k,_=ca.ctx_id(uu,cur,c0,t0,bit,mode);b=ad.decode(int(z[k]),int(o[k]));cur[c0,t0]=b
            if b:o[k]+=1
            else:z[k]+=1
        uu|=cur.astype(np.uint64)<<bit
    return m.unzig(uu).astype(np.int32),pos


def reproduce_best(X,eps):
    h,Q,D,dts,dcs,co,intercept,prior=ca.build_pair_state(X,eps);lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy())
    Q2,D2,_,single_changes=a.shape_search(Q2,lo,hi,D2,dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,a.PASSES)
    Q3,D3,_,pair_changes,tested,rejected=p.pair_search(np.ascontiguousarray(Q2.copy()),lo,hi,np.ascontiguousarray(D2.copy()),dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,1)
    Dr=g._all_defects(Q3,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D3):raise RuntimeError('reproduced best defect mismatch')
    return h,Q3,D3,dts,dcs,co,intercept,{'prior':prior,'single_changes':int(single_changes),'pair_changes':int(pair_changes),'tested':int(tested),'rejected':int(rejected)}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,search=reproduce_best(X,eps)
    # Reconfirm the pre-compaction exact incumbent on the same state.
    ob,_,OD,odetail=ca.causal_frame(D);old=c.validate(X,eps,h,Q,OD,dts,dcs,co,intercept,ob,'old_framed_causal',odetail)
    model,ddt,ddc,dco,dinter,md=compact_model(dts,dcs,co,intercept);defect,ddetail=compact_defect(D)
    # Codec identifier/version is one byte. Shape and epsilon are external decode arguments, matching the benchmark API contract used by SZ3.
    stream=bytes([VERSION])+model+defect
    pos=0
    if stream[pos]!=VERSION:raise RuntimeError('version');pos+=1
    # Decode compact model from the stream without a model-length side channel: tap-set rank has fixed public width and exactly K signed coefficients + intercept follow.
    rank2=int.from_bytes(stream[pos:pos+SET_BYTES],'little');pos+=SET_BYTES;ids2=unrank_combination(rank2,NGRAM,K);co2=[]
    for _ in range(K):q,pos=get_svar(stream,pos);co2.append(q)
    inter2,pos=get_svar(stream,pos);ddt2=np.asarray([OFFS[i][0] for i in ids2],np.int16);ddc2=np.asarray([OFFS[i][1] for i in ids2],np.int16);dco2=np.asarray(co2,np.int32)
    DD,pos=decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream):raise RuntimeError(('container trailing',pos,len(stream)))
    if not np.array_equal(DD,D):raise RuntimeError('compact defect mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=g._pred(Qd,c0,t,ddt2,ddc2,dco2,int(inter2),g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('compact Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=len(stream);result={'bytes':total,'bps':8*total/X.size,'maxerr':me,'model_bytes':len(model),'defect_bytes':len(defect),'version_bytes':1,'gain_vs_ar32':arb['bytes']/total,'gain_vs_sz3':szb/total,'delta_vs_ar32':total-arb['bytes'],'delta_vs_old':total-old['bytes']}
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'public_codec_config':{'h_factor':1.5,'scale_q12':g.SCALE,'ntaps':K,'tap_grammar_size':NGRAM,'shape_external':True,'epsilon_external':True},'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'old':old,'compact':result,'model_detail':md,'defect_detail':ddetail,'search':search,'scope':'Fully materialized compact NOVA container on the exact PR543 best hard-Imperial legal reconstruction. No information needed under the benchmark decode contract is dropped. As in the matched SZ3 API, array shape and requested epsilon are external decoder arguments; h=1.5*epsilon, Q12 scale, tap count and candidate tap grammar are fixed public codec configuration. The 20 selected generator taps are encoded exactly as one combinatorial rank among C(112,20) public tap sets, with coefficients/intercept as signed varints. Defect planes keep PR537 decoder-shared adaptive arithmetic but pack each mode/order/compression selector and final-byte bit count into one byte plus a varint payload length. Decoder parses the literal byte stream, reconstructs model and every defect bitplane, causally regenerates exact Q, and verifies the unchanged source hard error. Only len(stream) is reported as compressed bytes.'}
    json.dump(out,open('imperial_compact_nova_container.json','w'),indent=2);print(json.dumps({'summary':{'old':old['bytes'],'compact':total,'ar32':arb['bytes'],'sz3':int(szb),'delta_ar32':total-arb['bytes'],'gain_ar32':arb['bytes']/total,'model':len(model),'defect':len(defect),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
