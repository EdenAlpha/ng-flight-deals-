import json,math,os,sys
import numpy as np

src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

class BW:
    def __init__(self):self.b=bytearray();self.a=0;self.n=0
    def put(self,v,k):
        self.a|=int(v)<<self.n;self.n+=int(k)
        while self.n>=8:self.b.append(self.a&255);self.a>>=8;self.n-=8
    def finish(self):
        if self.n:self.b.append(self.a&255)
        return bytes(self.b)
class BR:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.a=0;self.n=0
    def get(self,k):
        k=int(k)
        while self.n<k:
            if self.i>=len(self.b):raise RuntimeError('bit EOF')
            self.a|=int(self.b[self.i])<<self.n;self.n+=8;self.i+=1
        m=(1<<k)-1;v=self.a&m;self.a>>=k;self.n-=k;return int(v)
def packk(a,k):
    w=BW()
    for x in np.asarray(a).tolist():w.put(int(x),k)
    return w.finish()
def unpackk(b,n,k):
    r=BR(b);return np.asarray([r.get(k) for _ in range(int(n))],np.int32)

def zz(a):
    a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzz(a):
    a=np.asarray(a,np.uint64);return ((a>>1).astype(np.int64)^(-((a&1).astype(np.int64))))

def trace_transform(inter,rc,kind):
    inter=np.asarray(inter,np.int64);out=np.empty_like(inter);k=0
    for n0 in np.asarray(rc).tolist():
        m=max(0,int(n0)-1)
        if not m:continue
        v=inter[k:k+m]
        if kind=='delta1':
            d=np.empty(m,np.int64);d[0]=v[0]
            if m>1:d[1:]=v[1:]-v[:-1]
            out[k:k+m]=zz(d).astype(np.int64)
        elif kind=='delta2':
            d=np.empty(m,np.int64);d[0]=v[0]
            if m>1:d[1]=v[1]-v[0]
            if m>2:d[2:]=v[2:]-2*v[1:-1]+v[:-2]
            out[k:k+m]=zz(d).astype(np.int64)
        elif kind=='xor':
            d=np.empty(m,np.int64);d[0]=v[0]
            if m>1:d[1:]=np.bitwise_xor(v[1:],v[:-1])
            out[k:k+m]=d
        else:raise ValueError(kind)
        k+=m
    if k!=len(inter):raise RuntimeError(('transform accounting',kind,k,len(inter)))
    return out.astype(np.int64)
def trace_inverse(code,rc,kind):
    code=np.asarray(code);out=np.empty(len(code),np.int64);k=0
    for n0 in np.asarray(rc).tolist():
        m=max(0,int(n0)-1)
        if not m:continue
        c=code[k:k+m]
        if kind in ('delta1','delta2'):d=unzz(c.astype(np.uint64))
        if kind=='delta1':
            v=np.empty(m,np.int64);v[0]=d[0]
            for j in range(1,m):v[j]=v[j-1]+d[j]
        elif kind=='delta2':
            v=np.empty(m,np.int64);v[0]=d[0]
            if m>1:v[1]=v[0]+d[1]
            for j in range(2,m):v[j]=d[j]+2*v[j-1]-v[j-2]
        elif kind=='xor':
            v=np.empty(m,np.int64);v[0]=int(c[0])
            for j in range(1,m):v[j]=int(c[j])^v[j-1]
        else:raise ValueError(kind)
        out[k:k+m]=v;k+=m
    if k!=len(code):raise RuntimeError(('inverse accounting',kind,k,len(code)))
    return out.astype(np.int32)

def enc_one(a,ctx,kind):
    s,_=reorder_vals(np.asarray(a),ctx);raw=leb_u(s);n,m,b,rows=compress_exact(raw);rr=leb_dec(decomp_one(b,m),len(s));R=restore_vals(rr,ctx).astype(np.int64)
    if not np.array_equal(R,np.asarray(a,np.int64)):raise RuntimeError(('single exact',kind))
    return {'name':kind,'bytes':int(n),'backend':METHOD_NAMES[int(m)],'pre_backend_bytes':len(raw)}
def enc_qr(inter,ctx,B):
    q=(inter//B).astype(np.int32);r=(inter%B).astype(np.int32);sq,_=reorder_vals(q,ctx);sr,_=reorder_vals(r,ctx);rq=leb_u(sq);k=int(math.log2(B));rr=packk(sr,k);cq=compress_exact(rq);cr=compress_exact(rr);dq=leb_dec(decomp_one(cq[2],cq[1]),len(sq));dr=unpackk(decomp_one(cr[2],cr[1]),len(sr),k);Q=restore_vals(dq,ctx).astype(np.int32);R=restore_vals(dr,ctx).astype(np.int32);x=Q*B+R
    if not np.array_equal(x,inter):raise RuntimeError(('qr exact',B))
    # One additional method byte + one uint64 length if integrated as a second frame.
    return {'name':f'quot-rem-{B}','bytes':int(cq[0]+cr[0]+9),'q_bytes':int(cq[0]),'r_bytes':int(cr[0]),'directory_bytes':9,'q_backend':METHOD_NAMES[int(cq[1])],'r_backend':METHOD_NAMES[int(cr[1])],'q_raw_bytes':len(rq),'r_raw_bytes':len(rr)}

def screen(K,current_container,parts):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER);rf=run_first_mask(rc);inter=(startg[~rf]-2).astype(np.int32);old=int(parts['inter_starts']);rows=[]
    for kind in ('delta1','delta2','xor'):
        code=trace_transform(inter,rc,kind);inv=trace_inverse(code,rc,kind)
        if not np.array_equal(inv,inter):raise RuntimeError(('transform exact',kind))
        for ck in range(10):
            ctx=refined_context(rc,lens,rcomp,ck);d=enc_one(code,ctx,f'{kind}:{context_name(ck)}');d.update({'transform':kind,'context_kind':ck,'context_name':context_name(ck)});rows.append(d)
    for B in (2,4,8,16,32,64):
        for ck in range(10):
            ctx=refined_context(rc,lens,rcomp,ck);d=enc_qr(inter,ctx,B);d.update({'context_kind':ck,'context_name':context_name(ck)});rows.append(d)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];pred=int(current_container-old+best['bytes']);return {'current_inter_bytes':old,'best':best,'all':rows,'predicted_container_bytes':pred,'saving':int(current_container-pred),'inter_count':int(len(inter))}

def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;G0,tm,outids,geom=geometry_map(X,gx,gy);arms=[]
    G,O=nearest_states(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);cur=TOP_HS+len(mb)+int(bo[0]);arms.append({'state':'nearest','current_bytes':cur,'screen':screen(K,cur,parts)})
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);cur=len(top);arms.append({'state':'phase16','current_bytes':cur,'screen':screen(K,cur,parts)})
    szb,sze=sz3_bytes(X,public_eps);rows=[]
    for a in arms:
        p=a['screen']['predicted_container_bytes'];rows.append({'state':a['state'],'current_bytes':a['current_bytes'],'current_inter_bytes':a['screen']['current_inter_bytes'],'transform':a['screen']['best']['name'],'new_inter_bytes':a['screen']['best']['bytes'],'predicted_bytes':p,'saving':a['screen']['saving'],'gain_vs_direct_sz3':float(szb/p),'clears_2x':bool(p<=szb/2),'screen':a['screen']})
    rows.sort(key=lambda r:r['predicted_bytes']);b=rows[0];out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'geometry':geom,'sz3':{'bytes':int(szb),'maxerr':float(sze)},'strict_two_x_target_bytes':szb/2,'best':b,'arms':rows}
    print(json.dumps({'target':out['strict_two_x_target_bytes'],'state':b['state'],'current':b['current_bytes'],'old_inter':b['current_inter_bytes'],'transform':b['transform'],'new_inter':b['new_inter_bytes'],'predicted':b['predicted_bytes'],'saving':b['saving'],'gain':b['gain_vs_direct_sz3'],'clears_2x':b['clears_2x']},indent=2),flush=True);json.dump(out,open('soda_tight_intergap_transform_screen.json','w'),indent=2)
main(sys.argv[1])
