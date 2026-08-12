import json,math,os,sys
import numpy as np

src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

class BitWriter:
    def __init__(self):self.buf=bytearray();self.acc=0;self.n=0
    def put(self,v,k):
        v=int(v);k=int(k);self.acc|=v<<self.n;self.n+=k
        while self.n>=8:self.buf.append(self.acc&255);self.acc>>=8;self.n-=8
    def finish(self):
        if self.n:self.buf.append(self.acc&255)
        return bytes(self.buf)
class BitReader:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.acc=0;self.n=0
    def get(self,k):
        while self.n<k:
            if self.i>=len(self.b):raise RuntimeError('bit EOF')
            self.acc|=int(self.b[self.i])<<self.n;self.n+=8;self.i+=1
        m=(1<<k)-1;v=self.acc&m;self.acc>>=k;self.n-=k;return int(v)

def pack_fixed(a,k):
    w=BitWriter()
    for x in np.asarray(a).tolist():w.put(int(x),k)
    return w.finish()
def unpack_fixed(b,n,k):
    r=BitReader(b);return np.asarray([r.get(k) for _ in range(int(n))],np.int32)

def encode_cut(lens,cut):
    lens=np.asarray(lens,np.int32);k=int(math.ceil(math.log2(cut+1)));code=np.minimum(lens-1,cut).astype(np.int32);esc=code==cut;tail=(lens[esc]-(cut+1)).astype(np.int32)
    return pack_fixed(code,k),leb_u(tail),{'cut':cut,'bits':k,'escape_count':int(esc.sum()),'escape_fraction':float(np.mean(esc)),'tail_raw_bytes':len(leb_u(tail))}
def decode_cut(a,b,n,cut):
    k=int(math.ceil(math.log2(cut+1)));code=unpack_fixed(a,n,k);esc=code==cut;tail=leb_dec(b,int(esc.sum())) if esc.any() else np.empty(0,np.int32);lens=code+1;lens[esc]=tail+(cut+1);return lens.astype(np.int32)

def comp(raw):
    n,m,b,rows=compress_exact(raw);return n,m,b,rows

def candidates(lens):
    lens=np.asarray(lens,np.int32);rows=[]
    # Direct exact length streams.
    raw=leb_u(lens);n,m,b,allr=comp(raw);rows.append({'name':'leb-length','bytes':int(n),'frames':1,'raw_bytes':len(raw),'method':METHOD_NAMES[m],'all':allr})
    if int(lens.max())<=255:
        raw=lens.astype(np.uint8).tobytes();n,m,b,allr=comp(raw);rows.append({'name':'uint8-length','bytes':int(n),'frames':1,'raw_bytes':len(raw),'method':METHOD_NAMES[m],'all':allr})
    for cut in (3,7,15,31,63):
        a,b,d=encode_cut(lens,cut);ra=comp(a);rb=comp(b);R=decode_cut(a,b,len(lens),cut)
        if not np.array_equal(R,lens):raise RuntimeError(('cut exact decode',cut))
        rows.append({'name':f'packed-cut-{cut}','bytes':int(ra[0]+rb[0]),'frames':2,'a_bytes':int(ra[0]),'b_bytes':int(rb[0]),'a_method':METHOD_NAMES[ra[1]],'b_method':METHOD_NAMES[rb[1]],'a_raw_bytes':len(a),'b_raw_bytes':len(b),'diag':d})
    rows.sort(key=lambda r:r['bytes']);return rows

def screen_arm(K,container_bytes,main_bytes,parts):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER);old=int(parts['long_support']+parts['very_support']+parts['long_residual']);rows=candidates(lens);best=rows[0];pred=int(container_bytes-old+best['bytes']);return {'current_length_bytes':old,'best':best,'all':rows,'predicted_container_bytes':pred,'predicted_saving_bytes':int(container_bytes-pred),'run_count':int(len(lens)),'max_run':int(lens.max()) if len(lens) else 0,'mean_run':float(np.mean(lens)) if len(lens) else 0.0}

def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy);arms=[]
    G,O=nearest_states(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);container=TOP_HS+len(mb)+int(bo[0]);arms.append({'state':'nearest','current_bytes':container,'screen':screen_arm(K,container,len(mb),parts)})
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);arms.append({'state':'phase16','current_bytes':len(top),'screen':screen_arm(K,len(top),len(mb),parts)})
    szb,sze=sz3_bytes(X,public_eps);rows=[]
    for a in arms:
        p=int(a['screen']['predicted_container_bytes']);rows.append({'state':a['state'],'current_bytes':a['current_bytes'],'current_length_bytes':a['screen']['current_length_bytes'],'length_name':a['screen']['best']['name'],'new_length_bytes':a['screen']['best']['bytes'],'predicted_bytes':p,'saving':a['screen']['predicted_saving_bytes'],'gain_vs_direct_sz3':float(szb/p),'clears_2x':bool(p<=szb/2),'screen':a['screen']})
    rows.sort(key=lambda r:r['predicted_bytes']);best=rows[0];out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'strict_two_x_target_bytes':szb/2,'best':best,'arms':rows}
    print(json.dumps({'target':out['strict_two_x_target_bytes'],'state':best['state'],'current':best['current_bytes'],'old_length':best['current_length_bytes'],'length_codec':best['length_name'],'new_length':best['new_length_bytes'],'predicted':best['predicted_bytes'],'saving':best['saving'],'gain':best['gain_vs_direct_sz3'],'clears_2x':best['clears_2x']},indent=2),flush=True);json.dump(out,open('soda_tight_runlength_screen.json','w'),indent=2)
main(sys.argv[1])
