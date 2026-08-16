import sys,json,struct
import h5py,numpy as np
import imperial_ar4_rich_adaptive_context_address as rich
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

a=rich.a
a.P=1
a.TRAIN=64
HEADER=32
SELECTOR=1
BASE_ADAPT=tuple(a.ADAPT)
BASE_AKEY=a.akey
LOWER=('known_prefix_low','known_prefix_low_t','known_prefix_low_tc','known_low_tc','known_prefix_low_t2')

def orders_for(nb):
    desc=tuple(range(nb-1,-1,-1));out=[('descending',desc)]
    for cut in (3,4,5,6):
        if cut>=nb:continue
        hi=tuple(range(nb-1,cut-1,-1));mid=tuple(range(cut-1,0,-1))
        out.append((f'high{cut}_zero_desc',hi+(0,)+mid))
        out.append((f'high{cut}_zero_asc',hi+(0,)+tuple(range(1,cut))))
    seen=[];ans=[]
    for x in out:
        if x[1] not in seen:seen.append(x[1]);ans.append(x)
    return ans

def lower_akey(known,B,bit,c,t,fam):
    if fam in BASE_ADAPT:return BASE_AKEY(known,B,bit,c,t,fam)
    prefix=int(known[c,t]>>(bit+1));lower=int(known[c,t]&((1<<bit)-1)) if bit>0 else 0
    pt=int(B[c,t-1]) if t>0 else 2;pc=int(B[c-1,t]) if c>0 else 2;pt2=int(B[c,t-2]) if t>1 else 2
    if fam=='known_prefix_low':return (prefix,lower)
    if fam=='known_prefix_low_t':return (prefix,lower,pt)
    if fam=='known_prefix_low_tc':return (prefix,lower,pt,pc)
    if fam=='known_low_tc':return (lower,pt,pc)
    if fam=='known_prefix_low_t2':return (prefix,lower,pt,pt2)
    raise ValueError(fam)

def ordered_frame(A,oid,order):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length())
    if tuple(sorted(order))!=tuple(range(nb)):raise RuntimeError(('bad order',nb,order))
    known=np.zeros_like(u,np.uint64);out=bytearray(struct.pack('<4sHHBB',b'HRO1',A.shape[0],A.shape[1],nb,oid));detail=[]
    for bit in order:
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'kind':'rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(a.ADAPT)):
            payload,d=a.encode_adaptive(B,known,bit,afid);row=(payload,{'kind':'adaptive',**d})
            if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail.append({'bit':int(bit),**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2,oid2=struct.unpack_from('<4sHHBB',buf,off);off+=10
    if magic!=b'HRO1' or (nc,nt)!=A.shape or nb2!=nb or oid2!=oid:raise RuntimeError('order header')
    dec_orders=orders_for(nb)
    if oid>=len(dec_orders) or dec_orders[oid][1]!=order:raise RuntimeError('order selector')
    uu=np.zeros_like(u,np.uint64)
    for bit in order:
        tag=buf[off];off+=1
        if tag<16:B,off=a.decode_rank_payload(buf,off,uu,bit,tag,A.shape)
        else:
            if tag>=16+len(a.ADAPT):raise RuntimeError(('tag',tag))
            B,off=a.decode_adaptive_payload(buf,off,uu,bit,tag,A.shape)
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('ordered replay')
    return len(buf),'ordered_hybrid',Ad,detail

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=a.build_ar8(X,eps)
    # First reproduce the richer descending-order floor before adding lower-plane contexts.
    stdb,stdn,stdK,stdd=a.hybrid_frame(K)
    if not np.array_equal(stdK,K):raise RuntimeError('standard K replay')
    stdme=a.replay(X,eps,cd,stdK,R);stdtotal=int(mb)+int(stdb)+HEADER+SELECTOR
    # Add contexts that can explicitly consume already-decoded lower planes under alternative orders.
    a.ADAPT=BASE_ADAPT+LOWER;a.akey=lower_akey
    u=m.zig(K);nb=max(1,int(u.max()).bit_length());rows=[]
    for oid,(name,order) in enumerate(orders_for(nb)):
        b,rep,Kd,detail=ordered_frame(K,oid,order)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',name))
        mer=a.replay(X,eps,cd,Kd,R);total=int(mb)+int(b)+HEADER+SELECTOR
        row={'order_id':oid,'order_name':name,'order':list(order),'bytes':total,'payload_bytes':int(b),'model_bytes':int(mb),'maxerr':mer,'delta_vs_standard':total-stdtotal,'detail':detail}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);obest=rows[0]
    if stdtotal<=obest['bytes']:
        chosen={'mode':'standard_descending','bytes':stdtotal,'payload_bytes':int(stdb),'model_bytes':int(mb),'maxerr':stdme,'detail':stdd}
    else:chosen={'mode':'ordered','order_name':obest['order_name'],'order':obest['order'],'bytes':obest['bytes'],'payload_bytes':obest['payload_bytes'],'model_bytes':obest['model_bytes'],'maxerr':obest['maxerr'],'detail':obest['detail']}
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':1,'train':64,'step':267,'standard_rich':{'bytes':stdtotal,'payload_bytes':int(stdb),'maxerr':stdme,'detail':stdd},'ordered_rows':rows,'chosen':chosen,'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'lower_contexts':list(LOWER),'gain_vs_old_ar32':old['bytes']/chosen['bytes'],'gain_vs_sz3':szb/chosen['bytes'],'scope':'Decoder-real NOVA coordinate-order gate on AR1/train64/step267. The standard PR600 richer descending bitplane order is reproduced exactly as a floor. Alternative public orders decode high planes first, then move bit0 earlier so later low magnitude planes may condition on it. New contexts may use the exact pattern of already decoded lower bits together with higher prefix and causal same-plane neighbors. Order identity is physically stored as one extra byte inside the ordered frame; no target-derived probability table is transmitted. Every candidate physically decodes the complete K field, causally replays AR1, and verifies the unchanged source hard-error bound.'}
    json.dump(out,open('imperial_ar1_bitplane_order_address.json','w'),indent=2)
    print(json.dumps({'summary':{'standard':stdtotal,'best_ordered':obest['bytes'],'best_order':obest['order_name'],'chosen':chosen['bytes'],'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_old_ar32':old['bytes']/chosen['bytes'],'gain_vs_sz3':szb/chosen['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
