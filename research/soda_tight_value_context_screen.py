import json,os,sys
import numpy as np

src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

MODES={0:'none',1:'phase',2:'component',3:'component-x-inside',4:'component-x-phase',6:'component-x-phase-plus-sign',7:'component-x-inside-plus-sign'}


def vctx(comp,phase,mode,signs=None,for_exception=False):
    comp=np.asarray(comp,np.int32);phase=np.asarray(phase,np.int32);inside=(phase!=0).astype(np.int32)
    if mode==0:base=np.zeros(comp.size,np.int32)
    elif mode==1:base=phase
    elif mode==2:base=comp
    elif mode in (3,7):base=comp*2+inside
    elif mode in (4,6):base=comp*4+phase
    else:raise ValueError(mode)
    if for_exception and mode in (6,7):
        if signs is None:raise RuntimeError('sign-conditioned context before signs')
        base=base*2+np.asarray(signs,bool).astype(np.int32)
    return base


def nctx(c):return int(np.max(c))+1 if len(c) else 1


def value_screen(K):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER);ne=vals.size;comp=np.repeat(rcomp.astype(np.int32),lens.astype(np.int64))
    if comp.size!=ne:raise RuntimeError(('event component accounting',comp.size,ne))
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    if k!=ne:raise RuntimeError('value trace accounting')
    repeat=(signs==prev)[rep_mask];ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);f6=np.packbits(firstsign,bitorder='little').tobytes();b6=best_comp(f6)[0][0]
    rows=[]
    for mode,name in MODES.items():
        rcx=vctx(comp[rep_mask],phase[rep_mask],mode);rs,_=reorder_bits(repeat,rcx);f7=np.packbits(rs,bitorder='little').tobytes();b7=best_comp(f7)[0][0]
        ecx=vctx(comp,phase,mode,signs,True);es,_=reorder_bits(exc,ecx);f8=np.packbits(es,bitorder='little').tobytes();b8=best_comp(f8)[0][0]
        mcx=ecx[exc];ms,_=reorder_vals(mag,mcx);dc=dtype_code(ms);raw9=ms.astype(DT[dc],copy=False).tobytes();br=best_comp(raw9)[0];opts=[(br[0],'raw-reordered',br[1],len(raw9))]
        rice,rd=rice_encode_context(mag,mcx,nctx(mcx));bb=best_comp(rice)[0];opts.append((bb[0],'rice-context',bb[1],len(rice)));opts.sort(key=lambda x:(x[0],x[1]));w=opts[0]
        total=b6+b7+b8+w[0]+1 # pessimistically charge one new mode byte
        rows.append({'mode':mode,'name':name,'value_bytes_plus_mode':total,'sign_first':b6,'sign_repeat':b7,'exception_support':b8,'exception_magnitude':w[0],'magnitude_rep':w[1],'magnitude_backend':METHOD_NAMES[w[2]],'magnitude_pre_backend_bytes':w[3],'repeat_contexts':nctx(rcx),'exception_contexts':nctx(ecx)})
    rows.sort(key=lambda r:r['value_bytes_plus_mode']);return rows


def states(X,tm,outids,shape,step,kind):
    if kind=='nearest':
        G=np.zeros(shape,np.int32)
        for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid].astype(np.float64)/step).astype(np.int32)
        return G,None
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,shape,step);return G,P


def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy);szb,sze=sz3_bytes(X,public_eps);outrows=[]
    for kind in ('nearest','phase'):
        G,P=states(X,tm,outids,G0.shape,step,kind);K=delta(G,3);mb,parts=prepare_refined_main(K)
        if decode_refined_main(mb).shape!=K.shape:raise RuntimeError('main audit shape')
        vrows=value_screen(K);best=vrows[0];current_value=int(parts['value_bytes']);pred_main=len(mb)-current_value+best['value_bytes_plus_mode'];phase_extra=0
        if kind=='phase':
            # Use exact PR #189 phase top overhead relative to main+outlier by recomputing the full phase arm.
            rr=eval_phase(X,tm,outids,G0.shape,internal_eps);phase_extra=int(rr['container_bytes']-rr['main_bytes']-rr['outlier_bytes'])
            outlier=int(rr['outlier_bytes'])
        else:
            rr=eval_no_phase(X,tm,outids,G0.shape,internal_eps);phase_extra=int(rr['container_bytes']-rr['main_bytes']-rr['outlier_bytes']);outlier=int(rr['outlier_bytes'])
        pred_container=pred_main+outlier+phase_extra
        outrows.append({'state_kind':kind,'current_main_bytes':len(mb),'current_value_bytes':current_value,'best_value':best,'all_value_modes':vrows,'predicted_main_bytes':pred_main,'outlier_bytes':outlier,'other_top_phase_bytes':phase_extra,'predicted_container_bytes':pred_container,'predicted_gain_vs_sz3':float(szb/pred_container),'two_x_target_bytes':szb/2,'predicted_clears_2x':bool(pred_container<=szb/2),'K_nonzero_fraction':float(np.mean(K!=0))})
    outrows.sort(key=lambda r:r['predicted_container_bytes']);out={'file':os.path.basename(path),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'raw_bytes':raw,'geometry':geom,'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'best_screen':outrows[0],'all_states':outrows,'note':'feasibility screen only; value bytes are exact compressed bytes but no new value-context decoder/container is claimed yet'}
    print(json.dumps({'best_state':outrows[0]['state_kind'],'best_mode':outrows[0]['best_value']['name'],'predicted_container':outrows[0]['predicted_container_bytes'],'predicted_gain':outrows[0]['predicted_gain_vs_sz3'],'target':outrows[0]['two_x_target_bytes'],'clears':outrows[0]['predicted_clears_2x'],'states':[{'state':r['state_kind'],'current_value':r['current_value_bytes'],'best_value':r['best_value']['value_bytes_plus_mode'],'saving':r['current_value_bytes']-r['best_value']['value_bytes_plus_mode'],'mode':r['best_value']['name'],'predicted_container':r['predicted_container_bytes']} for r in outrows]},indent=2),flush=True);json.dump(out,open('soda_tight_value_context_screen.json','w'),indent=2)

main(sys.argv[1])
