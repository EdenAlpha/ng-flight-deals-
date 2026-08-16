import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_persistent_ar32_full_array_jit as aj

T0=14488
C0=512
C=32
T=4096
TRAIN=1024
P=32
STEP=267
OUTER_HEADER=32
MAGIC=b'NLS1'

aj.m.P=32
aj.m.m.STEP=STEP

# ---------- compact integer/framing helpers ----------
def uvar(v):
    v=int(v)
    if v<0:raise ValueError(v)
    o=bytearray()
    while True:
        b=v&127;v>>=7
        if v:o.append(b|128)
        else:o.append(b);break
    return bytes(o)

def read_uvar(buf,pos):
    v=0;s=0
    while True:
        if pos>=len(buf):raise RuntimeError('uvar eof')
        b=buf[pos];pos+=1;v|=(b&127)<<s
        if not (b&128):return v,pos
        s+=7
        if s>63:raise RuntimeError('uvar overflow')

def pack_blob(raw):
    raw=bytes(raw);z=m.Z.compress(raw)
    return (b'\x01'+z) if len(z)<len(raw) else (b'\x00'+raw)

def unpack_blob(blob):
    if not blob:raise RuntimeError('empty blob')
    if blob[0]==0:return bytes(blob[1:])
    if blob[0]==1:return m.D.decompress(bytes(blob[1:]))
    raise RuntimeError(('blob flag',blob[0]))

def encode_gaps(ix):
    ix=np.asarray(ix,np.int64);o=bytearray();prev=-1
    for x in ix:
        x=int(x);o+=uvar(x-prev-1);prev=x
    return bytes(o)

def decode_gaps(raw,k):
    out=np.empty(k,np.int64);p=0;prev=-1
    for i in range(k):
        g,p=read_uvar(raw,p);prev=prev+1+g;out[i]=prev
    if p!=len(raw):raise RuntimeError(('gap trailing',p,len(raw)))
    return out

def runs_1d(flags,break_every=None):
    flags=np.asarray(flags,bool).ravel();runs=[]
    if break_every is None:
        starts=np.flatnonzero(flags & np.r_[True,~flags[:-1]])
        ends=np.flatnonzero(flags & np.r_[~flags[1:],True])+1
        return list(zip(starts.tolist(),(ends-starts).tolist()))
    n=len(flags)
    for base in range(0,n,break_every):
        z=flags[base:min(base+break_every,n)]
        if not z.size:continue
        starts=np.flatnonzero(z & np.r_[True,~z[:-1]])
        ends=np.flatnonzero(z & np.r_[~z[1:],True])+1
        runs.extend((base+int(a),int(b-a)) for a,b in zip(starts,ends))
    return runs

def encode_runs(runs):
    o=bytearray();o+=uvar(len(runs));prev_end=0
    for st,ln in runs:
        st=int(st);ln=int(ln)
        if st<prev_end or ln<=0:raise RuntimeError('bad run')
        o+=uvar(st-prev_end);o+=uvar(ln);prev_end=st+ln
    return bytes(o)

def decode_runs(raw,n):
    p=0;nr,p=read_uvar(raw,p);out=np.zeros(n,bool);prev_end=0
    for _ in range(nr):
        g,p=read_uvar(raw,p);ln,p=read_uvar(raw,p);st=prev_end+g;en=st+ln
        if en>n or ln<=0:raise RuntimeError(('run bounds',st,en,n))
        out[st:en]=True;prev_end=en
    if p!=len(raw):raise RuntimeError(('run trailing',p,len(raw)))
    return out

# ---------- exact constrained subset address ----------
def core_frames(target,active,shape):
    target=np.asarray(target,bool).ravel();active=np.asarray(active,bool).ravel()
    if np.any(target & ~active):raise RuntimeError('target outside active universe')
    ai=np.flatnonzero(active);flags=target[ai];k=int(flags.sum());nactive=len(ai);C0,T0=shape
    cands=[]
    # 0: bitmap only over the currently surviving universe.
    raw=np.packbits(flags.astype(np.uint8),bitorder='little').tobytes()
    cands.append((0,pack_blob(raw),'active_bitmap'))
    # 1: constrained-universe ranks of the selected survivors.
    ranks=np.flatnonzero(flags)
    cands.append((1,pack_blob(encode_gaps(ranks)),'active_rank_delta'))
    # 2: runs in constrained-universe rank order.
    cands.append((2,pack_blob(encode_runs(runs_1d(flags))),'active_rank_runs'))
    # 3: physical channel-major row spans.
    cands.append((3,pack_blob(encode_runs(runs_1d(target,break_every=T0))),'physical_time_runs'))
    # 4: physical time-major/channel spans.
    tr=target.reshape(C0,T0).T.reshape(-1)
    cands.append((4,pack_blob(encode_runs(runs_1d(tr,break_every=C0))),'physical_channel_runs'))
    # 5: physical linear coordinate deltas.
    cands.append((5,pack_blob(encode_gaps(np.flatnonzero(target))),'physical_coord_delta'))
    rows=[]
    for mode,body,name in cands:
        fr=bytes([mode])+uvar(k)+uvar(len(body))+body
        rows.append((len(fr),fr,name,k,nactive))
    return sorted(rows,key=lambda x:x[0])

def encode_subset(mask,active,shape):
    mask=np.asarray(mask,bool).ravel();active=np.asarray(active,bool).ravel();n=int(active.sum());k=int(mask.sum())
    if k==0:return b'\xff',{'mode':'none','encoded_count':0,'universe':n,'complement':False,'bytes':1}
    if k==n and np.array_equal(mask,active):return b'\xfe',{'mode':'all','encoded_count':n,'universe':n,'complement':False,'bytes':1}
    best=core_frames(mask,active,shape)[0]
    comp=active & ~mask
    cbest=core_frames(comp,active,shape)[0]
    if cbest[0]<best[0]:
        ln,fr,name,kk,nn=cbest;fr=bytes([fr[0]|0x80])+fr[1:]
        return fr,{'mode':name,'encoded_count':kk,'universe':nn,'complement':True,'bytes':len(fr)}
    ln,fr,name,kk,nn=best
    return fr,{'mode':name,'encoded_count':kk,'universe':nn,'complement':False,'bytes':len(fr)}

def decode_subset(buf,pos,active,shape):
    active=np.asarray(active,bool).ravel();n=len(active);C0,T0=shape
    if pos>=len(buf):raise RuntimeError('subset eof')
    tag=buf[pos];pos+=1
    if tag==0xff:return np.zeros(n,bool),pos,{'mode':'none'}
    if tag==0xfe:return active.copy(),pos,{'mode':'all'}
    comp=bool(tag&0x80);mode=tag&0x7f
    k,pos=read_uvar(buf,pos);bl,pos=read_uvar(buf,pos)
    if pos+bl>len(buf):raise RuntimeError('subset body eof')
    raw=unpack_blob(buf[pos:pos+bl]);pos+=bl
    ai=np.flatnonzero(active);na=len(ai);target=np.zeros(n,bool)
    if mode==0:
        flags=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:na].astype(bool)
        if len(raw)!=(na+7)//8:raise RuntimeError(('bitmap length',len(raw),na))
        target[ai[flags]]=True
    elif mode==1:
        ranks=decode_gaps(raw,k)
        if ranks.size and int(ranks[-1])>=na:raise RuntimeError('active rank overflow')
        target[ai[ranks]]=True
    elif mode==2:
        flags=decode_runs(raw,na)
        target[ai[flags]]=True
    elif mode==3:
        target=decode_runs(raw,n)
    elif mode==4:
        tr=decode_runs(raw,n).reshape(T0,C0)
        target=tr.T.reshape(-1)
    elif mode==5:
        ix=decode_gaps(raw,k)
        if ix.size and int(ix[-1])>=n:raise RuntimeError('physical rank overflow')
        target[ix]=True
    else:raise RuntimeError(('subset mode',mode))
    if int(target.sum())!=k or np.any(target & ~active):raise RuntimeError(('subset decode invalid',mode,k,int(target.sum())))
    if comp:target=active & ~target
    return target,pos,{'mode':mode,'complement':comp}

# ---------- nested magnitude / sign address ----------
def class_orders(mag,shape):
    vals,cnt=np.unique(mag,return_counts=True);vals=[int(x) for x in vals];counts={int(v):int(n) for v,n in zip(vals,cnt)}
    orders=[]
    orders.append(('ascending',tuple(sorted(vals))))
    orders.append(('descending',tuple(sorted(vals,reverse=True))))
    orders.append(('rare_first',tuple(sorted(vals,key=lambda v:(counts[v],v)))) ) # common class becomes implicit final class
    orders.append(('common_first',tuple(sorted(vals,key=lambda v:(-counts[v],v)))) )
    full=np.ones(mag.size,bool);cost={}
    for v in vals:
        fr,_=encode_subset(mag==v,full,shape);cost[v]=len(fr)
    orders.append(('cheap_first',tuple(sorted(vals,key=lambda v:(cost[v],v)))) ) # hardest class implicit
    orders.append(('expensive_first',tuple(sorted(vals,key=lambda v:(-cost[v],v)))) )
    seen=set();out=[]
    for name,o in orders:
        if o not in seen:seen.add(o);out.append((name,o))
    return out,counts,cost

def build_address(K,order_name,order,shape):
    K=np.asarray(K,np.int32);flat=K.ravel();mag=np.abs(flat.astype(np.int64));active=np.ones(flat.size,bool)
    s=bytearray(MAGIC);s+=uvar(shape[0])+uvar(shape[1])+uvar(len(order))
    for v in order:s+=uvar(v)
    details=[]
    for level,v in enumerate(order[:-1]):
        rm=active & (mag==int(v));fr,meta=encode_subset(rm,active,shape);s+=fr
        meta.update({'kind':'magnitude_removal','value':int(v),'level':level,'removed':int(rm.sum())});details.append(meta)
        active &= ~rm
    final=int(order[-1]);
    if not np.all(mag[active]==final) or int(active.sum())!=int(np.sum(mag==final)):raise RuntimeError(('final class mismatch',final))
    nonzero=mag>0;positive=flat>0
    signfr,signmeta=encode_subset(positive,nonzero,shape);s+=signfr
    signmeta.update({'kind':'positive_sign','positive':int(positive.sum()),'nonzero':int(nonzero.sum())});details.append(signmeta)
    raw=bytes(s);z=m.Z.compress(raw)
    if len(z)<len(raw):container=b'\x01'+z;outer='zstd'
    else:container=b'\x00'+raw;outer='raw'
    return container,{'order_name':order_name,'order':[int(x) for x in order],'raw_address_bytes':len(raw),'container_bytes':len(container),'outer_rep':outer,'frames':details}

def decode_address(container):
    if not container:raise RuntimeError('address empty')
    raw=m.D.decompress(container[1:]) if container[0]==1 else bytes(container[1:])
    if raw[:4]!=MAGIC:raise RuntimeError('address magic')
    pos=4;Cc,pos=read_uvar(raw,pos);Tt,pos=read_uvar(raw,pos);nc,pos=read_uvar(raw,pos);order=[]
    for _ in range(nc):v,pos=read_uvar(raw,pos);order.append(int(v))
    n=Cc*Tt;active=np.ones(n,bool);mag=np.empty(n,np.int64);mag.fill(-1)
    for v in order[:-1]:
        rm,pos,_=decode_subset(raw,pos,active,(Cc,Tt));mag[rm]=v;active &= ~rm
    mag[active]=order[-1]
    nonzero=mag>0;positive,pos,_=decode_subset(raw,pos,nonzero,(Cc,Tt))
    if pos!=len(raw):raise RuntimeError(('address trailing bytes',pos,len(raw)))
    out=np.zeros(n,np.int32);out[nonzero]=-mag[nonzero].astype(np.int32);out[positive]=mag[positive].astype(np.int32)
    return out.reshape(Cc,Tt)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co)
    R,K=aj.build(X,cd);fr=m.encode_k(K);Kd=np.asarray(fr[2],np.int32);Rd=aj.decode(Kd,cd)
    if not np.array_equal(Rd,R):raise RuntimeError('AR32 baseline replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR32 hard error',me,eps))
    baseline=int(mb)+int(fr[0])+OUTER_HEADER
    szb,ori=m.szrun(X,eps)
    mag=np.abs(K.astype(np.int64)).ravel();orders,counts,standalone=class_orders(mag,(C,T));rows=[]
    for name,order in orders:
        container,meta=build_address(K,name,order,(C,T));KD=decode_address(container)
        if not np.array_equal(KD,K):raise RuntimeError(('nested address K mismatch',name))
        R2=aj.decode(KD,cd)
        if not np.array_equal(R2,R):raise RuntimeError(('nested AR replay',name))
        me2=float(np.max(np.abs(X-R2.astype(np.float64))))
        if me2>eps*(1+5e-6):raise RuntimeError(('nested hard',name,me2,eps))
        total=int(mb)+len(container)+OUTER_HEADER
        modes={}
        comp=0
        for q in meta['frames']:
            modes[q['mode']]=modes.get(q['mode'],0)+1;comp+=int(q.get('complement',False))
        row={'order_name':name,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':len(container),'address_raw_bytes':meta['raw_address_bytes'],'outer_rep':meta['outer_rep'],'gain_vs_ar32':baseline/total,'gain_vs_sz3':szb/total,'maxerr':me2,'mode_counts':modes,'complement_frames':comp,'class_order':meta['order']};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='class_order'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','t0':T0,'c0':C0,'shape':[C,T],'samples':int(X.size),'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'ar_model_bytes':int(mb),'ar32':{'bytes':baseline,'bps':8*baseline/X.size,'innovation_bytes':int(fr[0]),'innovation_rep':fr[1],'maxerr':me,'zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'max_abs_k':int(np.max(np.abs(K)))},'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'magnitude_classes':len(counts),'magnitude_histogram':{str(k):v for k,v in counts.items()},'standalone_full_universe_class_bytes':{str(k):int(v) for k,v in standalone.items()},'best':best,'rows':rows,'scope':'Exact Layer-3 nested-level-set address for the incumbent shared AR32 step267 reconstruction. No predictor or reconstruction is changed. The exact AR32 innovation magnitude field is represented as a shrinking constrained universe: each emitted frame specifies which currently surviving physical positions leave the magnitude set next, while the final class is implicit. The encoder spends compute choosing among ascending/descending/frequency/codelength class orders. Every subset competes among active-universe bitmap, active-rank delta, active-rank runs, physical time/channel runs and physical coordinate deltas; complements are allowed because the active universe is decoder-known. Each frame is self-decoding and may be Zstd-compressed; the entire resulting address is then compressed again as a recursive-address stage. A final constrained subset assigns positive signs. The address is independently decoded to exact K, the AR32 state is replayed exactly, and the unchanged source hard-error bound is verified. Model bytes and outer framing are charged identically to the incumbent. Matched SZ3 is rerun on the same hard 32x4096 tile. This is a geometry/constrained-address test, not an oracle and not a new predictor.'}
    json.dump(out,open('imperial_ar32_nested_levelset_address.json','w'),indent=2)
    print(json.dumps({'summary':{'nested_bytes':best['bytes'],'ar32_bytes':baseline,'sz3_bytes':int(szb),'gain_ar32':best['gain_vs_ar32'],'gain_sz3':best['gain_vs_sz3'],'order':best['order_name'],'address_bytes':best['address_bytes'],'outer_rep':best['outer_rep'],'mode_counts':best['mode_counts']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
