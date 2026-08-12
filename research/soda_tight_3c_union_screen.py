import json,math,os,sys
import numpy as np

src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

ORDER=(0,1,2);CTXMODE=4

def pack3(a):
    a=np.asarray(a,np.uint8).ravel()
    if a.size and (np.min(a)<0 or np.max(a)>7):raise RuntimeError('pack3 domain')
    bits=np.empty(a.size*3,np.uint8)
    bits[0::3]=a&1;bits[1::3]=(a>>1)&1;bits[2::3]=(a>>2)&1
    return np.packbits(bits,bitorder='little').tobytes()

def unpack3(b,n):
    bits=np.unpackbits(np.frombuffer(b,np.uint8),bitorder='little',count=n*3)
    return (bits[0::3]|(bits[1::3]<<1)|(bits[2::3]<<2)).astype(np.uint8)

def entropy_bits(vals):
    vals=np.asarray(vals)
    if not vals.size:return 0.0,0.0
    _,c=np.unique(vals,return_counts=True);p=c/c.sum();H=float(-np.sum(p*np.log2(p)))
    return H,H*vals.size

def best_current(K):
    cache=structural_sequences(K);rows=[]
    for r2 in (0,1):
        for r9 in (0,1):
            b,parts=encode_main_candidate(K,r2,r9,cache);R=decode_main_candidate(b)
            if not np.array_equal(R,K):raise RuntimeError(('current K decode',r2,r9))
            rows.append((len(b),r2,r9,b,parts))
    rows.sort(key=lambda r:r[0]);return rows[0]

def union_sequences(K):
    if K.shape[0]!=3:raise RuntimeError(('requires 3C',K.shape))
    active=K!=0;mask=(active[0].astype(np.uint8)|(active[1].astype(np.uint8)<<1)|(active[2].astype(np.uint8)<<2));union=mask!=0
    U=union.astype(np.int32)[None,...]
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(U,ORDER)
    # gather masks in exactly the same singleton-component trace/event order.
    mseq=[]
    for l in range(mask.shape[0]):
        for s in range(mask.shape[1]):
            pos=np.flatnonzero(union[l,s])
            if pos.size:mseq.extend(mask[l,s,pos].tolist())
    mseq=np.asarray(mseq,np.uint8)
    if mseq.size!=vals.size or not np.all(vals==1):raise RuntimeError(('union event ordering',mseq.size,vals.size))
    return U,mseq,phase,diag,mask

def compressed_union_timing(U):
    sh,dc,rawframes,meta=prepare_raw_frames(U,ORDER,CTXMODE);frames=[];choices=[]
    for i,r in enumerate(rawframes[:6]):
        best,allrows=best_comp(r);n,m,b=best;frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    return sum(len(x) for x in frames),choices,meta

def mask_candidates(mseq,phase):
    if not np.array_equal(unpack3(pack3(mseq),mseq.size),mseq):raise RuntimeError('pack3 roundtrip')
    rows=[]
    def add(name,raw,extra=0):
        best,allrows=best_comp(raw);n,m,b=best;rows.append({'name':name,'bytes':int(n+extra),'payload_bytes':int(n),'metadata_bytes':int(extra),'raw_bytes':len(raw),'chosen':METHOD_NAMES[m],'all':allrows})
    add('uint8_trace_order',mseq.tobytes())
    add('packed3_trace_order',pack3(mseq))
    p=np.argsort(phase,kind='stable');add('packed3_runphase_reordered',pack3(mseq[p]))
    # Four decoder-visible run-phase groups, separately backend-compressed.
    total=0;details=[]
    for ph in range(4):
        raw=pack3(mseq[phase==ph]);best,allrows=best_comp(raw);n,m,b=best;total+=n;details.append({'phase':ph,'n':int(np.sum(phase==ph)),'bytes':n,'chosen':METHOD_NAMES[m]})
    rows.append({'name':'packed3_split_runphase','bytes':int(total+4*4),'payload_bytes':int(total),'metadata_bytes':16,'raw_bytes':sum((int(np.sum(phase==ph))*3+7)//8 for ph in range(4)),'chosen':'per-phase','details':details})
    rows.sort(key=lambda r:r['bytes']);return rows

def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    K=delta(G,3);cur=best_current(K);U,mseq,phase,udiag,mask=union_sequences(K);utim,utim_choices,umeta=compressed_union_timing(U);mc=mask_candidates(mseq,phase);mbest=mc[0]
    total_events=int(np.count_nonzero(K));union_events=int(mseq.size);multi=int(np.sum((mask!=0)&((mask&(mask-1))!=0)));single=union_events-multi
    Hmask,Hbits=entropy_bits(mseq);freq={str(i):int(np.sum(mseq==i)) for i in range(1,8)}
    current_timing=int(cur[4]['timing_bytes']);current_values=int(cur[4]['value_bytes']);union_timing_plus_mask=int(utim+mbest['bytes']);predicted_main=int(cur[4]['header_bytes']+union_timing_plus_mask+current_values)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':int(X.nbytes),'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'component_events':total_events,'union_events':union_events,'component_events_removed_by_union':total_events-union_events,'union_event_fraction_of_component_events':float(union_events/max(1,total_events)),'multi_component_union_events':multi,'multi_component_union_fraction':float(multi/max(1,union_events)),'single_component_union_events':single,'mask_frequency':freq,'mask_entropy_bits_per_union_event':Hmask,'mask_zero_order_entropy_bytes':Hbits/8.0,'current':{'main_bytes':int(cur[0]),'timing_bytes':current_timing,'value_bytes':current_values,'inter_rice':bool(cur[1]),'magnitude_rice':bool(cur[2]),'parts':cur[4]},'union':{'timing_bytes':int(utim),'timing_backend_choices':utim_choices,'timing_meta':umeta,'mask_best':mbest,'mask_candidates':mc,'timing_plus_mask_bytes':union_timing_plus_mask,'predicted_main_bytes_if_values_unchanged':predicted_main,'predicted_saving_vs_current_main':int(cur[0]-predicted_main),'predicted_improvement_ratio':float(cur[0]/predicted_main)}}
    print(json.dumps({'frac':frac,'component_events':total_events,'union_events':union_events,'multi_fraction':out['multi_component_union_fraction'],'current_timing':current_timing,'union_timing':utim,'mask_bytes':mbest['bytes'],'union_plus_mask':union_timing_plus_mask,'predicted_main':predicted_main,'current_main':cur[0],'predicted_saving':out['union']['predicted_saving_vs_current_main'],'mask_entropy_bpe':Hmask,'mask_best':mbest['name']},indent=2),flush=True)
    json.dump(out,open('soda_tight_3c_union_screen.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
