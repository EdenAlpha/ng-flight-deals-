import json,os,struct,sys
import numpy as np

# Reuse PR #161's verified codec and its full decoder.  The strict arm below
# freezes the p75-winning structural representation AND the exact ten p75
# backend IDs.  The adaptive arm keeps only PR #161's already-decoder-visible
# fixed seven-backend menu and is reported separately.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

FROZEN_METHODS=(3,3,3,3,3,3,0,3,3,3)  # p75 PR #161: Brotli11 except raw first-sign
FROZEN_ORDER=(0,1,2)
FROZEN_CTXMODE=4


def encode_main_fixed(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,FROZEN_ORDER,FROZEN_CTXMODE)
    methods=list(FROZEN_METHODS);frames=[];choices=[]
    for i,(r,m) in enumerate(zip(rawframes,methods)):
        b=comp_one(r,m)
        if decomp_one(b,m)!=r:raise RuntimeError(('fixed backend roundtrip',i,m))
        frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'method':METHOD_NAMES[m],'bytes':len(b)})
    oc=int(FROZEN_ORDER[0]|(FROZEN_ORDER[1]<<2)|(FROZEN_ORDER[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,FROZEN_CTXMODE,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude']
    parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=HHS;parts['backend_choices']=choices;parts.update(meta)
    return h+b''.join(frames),parts


def reconstruct_and_measure(X,G,tm,outids,O,RK,RO,step):
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step)
    return float(np.max(np.abs(X-Y)))


def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=int(X.nbytes)
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)

    # Existing outlier dictionary is unchanged from the audited codec.  It is
    # decoder-visible and charged identically to both strict/adaptive main arms.
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')
    out_bytes=int(bo[0])

    fb,fparts=encode_main_fixed(K);FR=decode_main(fb)
    if not np.array_equal(FR,K):raise RuntimeError('frozen main exact K')
    fme=reconstruct_and_measure(X,G,tm,outids,O,FR,RO,step)
    fcontainer=TOPS+len(fb)+out_bytes

    ab,aparts=encode_main(K,FROZEN_ORDER,FROZEN_CTXMODE);AR=decode_main(ab)
    if not np.array_equal(AR,K):raise RuntimeError('adaptive main exact K')
    ame=reconstruct_and_measure(X,G,tm,outids,O,AR,RO,step)
    acontainer=TOPS+len(ab)+out_bytes

    szb,sze=sz3_bytes(X,eps)
    out={
      'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'step':step,
      'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),
      'frozen_definition':{'order':list(FROZEN_ORDER),'context_mode':FROZEN_CTXMODE,'backend_method_ids':list(FROZEN_METHODS),'backend_methods':[METHOD_NAMES[x] for x in FROZEN_METHODS]},
      'frozen':{'main_bytes':len(fb),'main_parts':fparts,'outlier_bytes':out_bytes,'top_header_bytes':TOPS,'container_bytes':fcontainer,'ratio':float(raw/fcontainer),'maxerr':fme,'valid':bool(fme<=eps*(1+3e-6)),'gain_vs_direct_sz3':float(szb/fcontainer)},
      'adaptive_backend_menu':{'main_bytes':len(ab),'main_parts':aparts,'outlier_bytes':out_bytes,'top_header_bytes':TOPS,'container_bytes':acontainer,'ratio':float(raw/acontainer),'maxerr':ame,'valid':bool(ame<=eps*(1+3e-6)),'gain_vs_direct_sz3':float(szb/acontainer)},
      'sz3_direct':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},
      'outlier_best':{'bytes':out_bytes,'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])}
    }
    if not out['frozen']['valid'] or not out['adaptive_backend_menu']['valid']:raise RuntimeError(('hard error failure',fme,ame,eps))
    print(json.dumps({'file':out['file'],'frozen_bytes':fcontainer,'frozen_ratio':out['frozen']['ratio'],'adaptive_bytes':acontainer,'adaptive_ratio':out['adaptive_backend_menu']['ratio'],'sz3_bytes':int(szb),'frozen_gain_sz3':out['frozen']['gain_vs_direct_sz3'],'adaptive_gain_sz3':out['adaptive_backend_menu']['gain_vs_direct_sz3'],'maxerr':fme,'eps':eps},indent=2),flush=True)
    json.dump(out,open('soda_hard4_frozen_record.json','w'),indent=2)

main(sys.argv[1])
