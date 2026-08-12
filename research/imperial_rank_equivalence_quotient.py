import json,sys
import h5py,numpy as np
import imperial_rank_motion_coordinate as m

GROUPS=(8,16,32,64,128)

def ordered_classes(Q,G):
    C,T=Q.shape;L=np.empty((C,T),np.int64);V=np.zeros((C,T),np.int64)
    for t in range(T):
        for g in range(0,C,G):
            vals,inv=np.unique(Q[g:g+G,t],return_inverse=True)
            L[g:g+G,t]=inv
            V[g:g+len(vals),t]=vals
    R=np.empty_like(Q)
    for t in range(T):
        for g in range(0,C,G):R[g:g+G,t]=V[g+L[g:g+G,t],t]
    if not np.array_equal(R,Q):raise RuntimeError('ordered class decode')
    return L,V

def persistent_palette(Q,G):
    C,T=Q.shape;L=np.empty((C,T),np.int64);V=np.zeros((C,T),np.int64)
    for g in range(0,C,G):
        vals,cur=np.unique(Q[g:g+G,0],return_inverse=True);ids=np.arange(len(vals),dtype=np.int64)
        L[g:g+G,0]=ids[cur]
        for j,v in enumerate(vals):V[g+ids[j],0]=v
        prev=L[g:g+G,0].copy()
        for t in range(1,T):
            vals,cur=np.unique(Q[g:g+G,t],return_inverse=True);nv=len(vals)
            overlap=np.zeros((G,nv),np.int16)
            for c in range(G):overlap[int(prev[c]),int(cur[c])]+=1
            pairs=[]
            for pid in range(G):
                for j in range(nv):
                    z=int(overlap[pid,j])
                    if z:pairs.append((-z,pid,j))
            pairs.sort();assigned_id=np.full(nv,-1,np.int64);used=np.zeros(G,bool)
            for neg,pid,j in pairs:
                if assigned_id[j]<0 and not used[pid]:assigned_id[j]=pid;used[pid]=True
            free=[i for i in range(G) if not used[i]];k=0
            for j in range(nv):
                if assigned_id[j]<0:assigned_id[j]=free[k];k+=1
            now=assigned_id[cur];L[g:g+G,t]=now
            for j,v in enumerate(vals):V[g+int(assigned_id[j]),t]=v
            prev=now.copy()
    R=np.empty_like(Q)
    for t in range(T):
        for g in range(0,C,G):R[g:g+G,t]=V[g+L[g:g+G,t],t]
    if not np.array_equal(R,Q):raise RuntimeError('persistent palette decode')
    return L,V

def label_stats(L):
    d=L[:,1:]-L[:,:-1]
    return {'label_unchanged_fraction':float(np.mean(d==0)),'mean_abs_label_motion':float(np.mean(np.abs(d)))}

def encode_scheme(Q,G,kind):
    if kind=='ordered':L,V=ordered_classes(Q,G)
    elif kind=='persistent':L,V=persistent_palette(Q,G)
    else:raise ValueError(kind)
    lb,lr=m.encode_array(L);vb,vr=m.encode_array(V);total=lb+vb+64
    R=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for g in range(0,Q.shape[0],G):R[g:g+G,t]=V[g+L[g:g+G,t],t]
    if not np.array_equal(R,Q):raise RuntimeError(('final decode',kind,G))
    s={'kind':kind,'bytes':total,'bps':8*total/Q.size,'label_bytes':lb,'label_bps':8*lb/Q.size,'label_rep':lr,'palette_bytes':vb,'palette_bps':8*vb/Q.size,'palette_rep':vr}
    s.update(label_stats(L));return s

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+m.T,c0:c0+m.C],np.float64).T;Q=np.rint(X/m.STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*m.STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            sb,ori=m.szrun(X,eps);fb,fr=m.encode_array(Q);tiles.append({'tile':name,'sz3_bytes':sb,'fixed256_bytes':fb,'fixed256_rep':fr})
            for G in GROUPS:
                for kind in ('ordered','persistent'):
                    r=encode_scheme(Q,G,kind);r.update({'tile':name,'group':G,'sz3_bytes':sb,'fixed256_bytes':fb,'gain_vs_sz3':sb/r['bytes'],'gain_vs_fixed256':fb/r['bytes'],'maxerr':me});rows.append(r);print(json.dumps(r),flush=True)
        n=m.C*m.T*len(tiles);szb=sum(x['sz3_bytes'] for x in tiles);fb=sum(x['fixed256_bytes'] for x in tiles);combos=[]
        for G in GROUPS:
            for kind in ('ordered','persistent'):
                rr=[r for r in rows if r['group']==G and r['kind']==kind];b=sum(r['bytes'] for r in rr)
                combos.append({'group':G,'kind':kind,'bytes':b,'bps':8*b/n,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,'label_bps':8*sum(r['label_bytes'] for r in rr)/n,'palette_bps':8*sum(r['palette_bytes'] for r in rr)/n,'median_label_unchanged':float(np.median([r['label_unchanged_fraction'] for r in rr])),'median_abs_label_motion':float(np.median([r['mean_abs_label_motion'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':m.STEP,'patch_shape':[m.C,m.T],'groups':list(GROUPS),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Exact equivalence-class quotient of the rank-coordinate experiment. Equal reconstructed amplitudes are indistinguishable, so no bits are spent ordering channels inside a tie. Ordered mode transmits a per-time unique-value palette plus physical-channel class labels. Persistent mode additionally assigns current amplitude classes to decoder-visible persistent palette IDs by deterministic maximum-overlap greedy matching against the previous labels, so amplitude classes may cross in value without forcing label IDs to swap. Decoder receives only the palette-value table and label field, both through the same self-decoding integer-frame menu, and reconstructs Q exactly before the <=128 hard-error check. All bytes/framing charged; matched SZ3 and fixed256 rerun. No AI; four-tile screen.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_rank_equivalence_quotient.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
