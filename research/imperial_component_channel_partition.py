import json,sys,struct
import h5py,numpy as np
import imperial_huber_ar32_component_zsm_gps as base

C=base.C; NT=base.NT; C0=base.C0; SCREEN=4096
GROUPS=(128,64,32,16,8,4,2,1)
CFG={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}
COMPONENTS=base.COMPONENTS
INCUMBENT=2468803


def enc(K,comp,W,nt,gr,G):
    n0=base.nctx(gr); ng=(C+G-1)//G; E=base.q.AE(n0*ng)
    ring=np.zeros((C,W),np.int32); sums=np.zeros(C,np.int64)
    for t in range(nt):
        rp=t%W; cnt=min(t,W)
        for c in range(C):
            ac=base.q.ac_state(sums[c],cnt); prev=int(K[c,t-1]) if t else 0; left=int(K[c-1,t]) if c else 0; diag=int(K[c-1,t-1]) if c and t else 0; k=int(K[c,t]); iz=(k==0)
            off=(c//G)*n0
            if comp=='zero': E.put(1 if iz else 0,off+base.cctx(gr,prev,left,diag,ac,comp))
            elif not iz:
                mag=abs(k); qq=mag.bit_length()-1
                if comp=='sign': E.put(1 if k<0 else 0,off+base.cctx(gr,prev,left,diag,ac,comp))
                elif comp=='pref':
                    for j in range(qq): E.put(0,off+base.cctx(gr,prev,left,diag,ac,comp,pos=j))
                    E.put(1,off+base.cctx(gr,prev,left,diag,ac,comp,pos=qq))
                elif comp=='suff':
                    rem=mag-(1<<qq)
                    for bp in range(qq-1,-1,-1): E.put((rem>>bp)&1,off+base.cctx(gr,prev,left,diag,ac,comp,qmag=qq,pos=qq-1-bp))
            old=int(ring[c,rp]); new=abs(k); ring[c,rp]=new; sums[c]+=new-old
    return E.finish()


def selector(gr,W,G): return base.config_id(gr,W)*len(GROUPS)+GROUPS.index(G)
def unselector(s):
    cid=s//len(GROUPS); gid=s%len(GROUPS); gr,W=base.config_from_id(cid); return gr,W,GROUPS[gid]


def decode(entries,shape):
    dec={}; cfg={}; rings={}; sums={}
    for comp,(sel,nb,bb) in entries.items():
        gr,W,G=unselector(sel); n0=base.nctx(gr); ng=(C+G-1)//G
        cfg[comp]=(gr,W,G,n0); dec[comp]=base.q.AD(bb,nb,n0*ng); rings[comp]=np.zeros((C,W),np.int32); sums[comp]=np.zeros(C,np.int64)
    K=np.zeros(shape,np.int32)
    for t in range(shape[1]):
        for c in range(C):
            prev=int(K[c,t-1]) if t else 0; left=int(K[c-1,t]) if c else 0; diag=int(K[c-1,t-1]) if c and t else 0
            acs={}
            for comp in COMPONENTS:
                gr,W,G,n0=cfg[comp]; cnt=min(t,W); acs[comp]=base.q.ac_state(sums[comp][c],cnt)
            gr,W,G,n0=cfg['zero']; off=(c//G)*n0
            iz=dec['zero'].get(off+base.cctx(gr,prev,left,diag,acs['zero'],'zero'))
            if iz: k=0
            else:
                gr,W,G,n0=cfg['sign']; off=(c//G)*n0
                neg=dec['sign'].get(off+base.cctx(gr,prev,left,diag,acs['sign'],'sign'))
                qq=0; gr,W,G,n0=cfg['pref']; off=(c//G)*n0
                while True:
                    b=dec['pref'].get(off+base.cctx(gr,prev,left,diag,acs['pref'],'pref',pos=qq))
                    if b: break
                    qq+=1
                    if qq>30: raise RuntimeError('gamma overflow')
                rem=0; gr,W,G,n0=cfg['suff']; off=(c//G)*n0
                for pos in range(qq): rem=(rem<<1)|dec['suff'].get(off+base.cctx(gr,prev,left,diag,acs['suff'],'suff',qmag=qq,pos=pos))
                mag=(1<<qq)+rem; k=-mag if neg else mag
            K[c,t]=k
            for comp in COMPONENTS:
                gr,W,G,n0=cfg[comp]; rp=t%W; old=int(rings[comp][c,rp]); new=abs(k); rings[comp][c,rp]=new; sums[comp][c]+=new-old
    return K


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; _,std=base.m.stats(d); eps=.1*std; X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=base.ah.fits(X); model,cod=base.model_frame(co); R,K=base.ah.run_ar(X,cod)
    screens={}; chosen={}; stream=bytearray()
    for comp in COMPONENTS:
        gr,W=CFG[comp]; rows=[]
        for G in GROUPS:
            bb,nb=enc(K,comp,W,SCREEN,gr,G); r={'component':comp,'grammar':gr,'W':W,'group':G,'prefix_bytes':len(bb),'prefix_bits':int(nb)}; rows.append(r); print(json.dumps(r),flush=True)
        rows.sort(key=lambda r:r['prefix_bytes']); best=rows[0]; screens[comp]=rows
        G=best['group']; bb,nb=enc(K,comp,W,NT,gr,G); sel=selector(gr,W,G)
        chosen[comp]={'grammar':gr,'W':W,'group':G,'payload_bytes':len(bb),'bits':int(nb),'selector':sel}; stream.extend(struct.pack('<BQI',sel,int(nb),len(bb))); stream.extend(bb)
    off=0; entries={}
    for comp in COMPONENTS:
        sel,nb,L=struct.unpack_from('<BQI',stream,off); off+=13; bb=bytes(stream[off:off+L]); off+=L; entries[comp]=(sel,int(nb),bb)
    if off!=len(stream): raise RuntimeError('trailing')
    Kd=decode(entries,K.shape)
    if not np.array_equal(Kd,K): raise RuntimeError('K replay')
    Rd=base.ah.decode_source(Kd,cod)
    if not np.array_equal(Rd,R): raise RuntimeError('AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6): raise RuntimeError(('hard',me,eps))
    total=base.OUTER_BYTES+len(model)+len(stream)
    out={'bytes':total,'incumbent_bytes':INCUMBENT,'delta':total-INCUMBENT,'gain_vs_incumbent':INCUMBENT/total,'matched_sz3_bytes':base.MATCHED_SZ3,'gain_vs_sz3':base.MATCHED_SZ3/total,'maxerr':me,'chosen':chosen,'screens':screens,
         'scope':'Exact full-hard Huber AR32 component codec with the incumbent grammar/window frozen per component and only decoder-causal channel partitioning added. Each component prefix-screens public group sizes 128..1. Group id is packed into the existing one-byte component selector, so no distribution tables or hidden side models are free. Exact K decode, source replay and hard error are mandatory.'}
    json.dump(out,open('imperial_component_channel_partition.json','w'),indent=2); print(json.dumps({'summary':{k:out[k] for k in ('bytes','incumbent_bytes','delta','gain_vs_incumbent','chosen','maxerr')}},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
