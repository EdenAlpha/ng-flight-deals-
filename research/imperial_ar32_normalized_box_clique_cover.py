import json,sys,math
import h5py,numpy as np,zstandard as zstd,networkx as nx
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_ar32_state_normalized_residual_support as s
import imperial_ar32_state_normalized_affine_atlas_cover as a
import imperial_decoder_phase_automaton as m

ZC=zstd.ZstdCompressor(level=22); ZD=zstd.ZstdDecompressor(); L=g.L


def exact_intervals(V,sc,eps):
    # q is a shared normalized codeword; decoder emits rint(q*decoder_scale).
    # These open-ish intervals are safely inside all q values whose integer replay is legal.
    rlo=np.ceil(V-eps).astype(np.int64); rhi=np.floor(V+eps).astype(np.int64)
    lo=(rlo.astype(np.float64)-0.499)/sc[:,None]; hi=(rhi.astype(np.float64)+0.499)/sc[:,None]
    return lo,hi,rlo,rhi


def graph_from_boxes(lo,hi):
    cen=(lo+hi)*0.5; half=(hi-lo)*0.5; mr=float(np.max(half))*2.000001
    raw=cKDTree(cen,compact_nodes=True,balanced_tree=True).query_pairs(r=mr,p=np.inf,output_type='ndarray')
    if len(raw):
        i,j=raw[:,0],raw[:,1]; ok=np.all(np.maximum(lo[i],lo[j])<=np.minimum(hi[i],hi[j]),axis=1); edges=raw[ok]
    else: edges=np.empty((0,2),np.int64)
    G=nx.Graph(); G.add_nodes_from(range(len(lo))); G.add_edges_from((int(i),int(j)) for i,j in edges)
    return G,edges,mr


def clique_partition(G):
    clusters=[]; maxcomp=0
    for comp in nx.connected_components(G):
        cc=list(comp); maxcomp=max(maxcomp,len(cc))
        if len(cc)==1: clusters.append(cc); continue
        sub=G.subgraph(cc).copy()
        # Clique cover of G == coloring of complement. Components are expected to be tiny/sparse;
        # DSATUR gives a strong constructive partition without pretending global optimality.
        if len(cc)<=400:
            col=nx.coloring.greedy_color(nx.complement(sub),strategy='saturation_largest_first')
            by={}
            for v,c in col.items(): by.setdefault(c,[]).append(v)
            clusters.extend(by.values())
        else:
            # Safe sparse fallback: greedily grow pairwise-compatible cliques.
            unseen=set(cc)
            while unseen:
                v=max(unseen,key=lambda q: sub.degree(q)); cl=[v]; cand=set(sub.neighbors(v))&unseen
                while cand:
                    w=max(cand,key=lambda q: len(cand & set(sub.neighbors(q))))
                    cl.append(w); cand &= set(sub.neighbors(w)); cand.discard(w)
                for q in cl: unseen.discard(q)
                clusters.append(cl)
    return clusters,maxcomp


def codewords_for_clusters(clusters,lo,hi,V,sc,eps):
    q=[]; ids=np.empty(len(V),np.int32); sizes=[]
    for ci,cl in enumerate(clusters):
        aa=np.asarray(cl,np.int64); L0=np.max(lo[aa],axis=0); H0=np.min(hi[aa],axis=0)
        if np.any(L0>H0+1e-12): raise RuntimeError(('nonclique',ci,len(cl)))
        qq=(L0+H0)*0.5; q.append(qq); ids[aa]=ci; sizes.append(len(cl))
    q=np.asarray(q,np.float64)
    # Find a compact fixed-point representation that still replays every assigned block legally.
    modes=[]
    for Q in (64,128,256,512,1024,2048,4096,8192,16384):
        qi=np.rint(q*Q).astype(np.int32); qr=qi.astype(np.float64)/Q
        rr=np.rint(qr[ids]*sc[:,None]).astype(np.int64); me=float(np.max(np.abs(rr-V)))
        legal=bool(me<=eps*(1+1e-12))
        if legal:
            raw=qi.astype('<i4').tobytes(); col=np.ascontiguousarray(qi.T).astype('<i4').tobytes()
            # Also try delta coding in deterministic cluster order.
            di=qi.copy(); di[1:]-=qi[:-1]; draw=di.astype('<i4').tobytes(); dcol=np.ascontiguousarray(di.T).astype('<i4').tobytes()
            streams=[('row',ZC.compress(raw)),('col',ZC.compress(col)),('drow',ZC.compress(draw)),('dcol',ZC.compress(dcol))]
            name,bb=min(streams,key=lambda z:len(z[1])); modes.append((len(bb),Q,name,bb,qi,me))
    if not modes: raise RuntimeError('no fixed-point codebook precision survived exact replay')
    cb,Q,layout,bb,qi,me=min(modes,key=lambda z:z[0])
    # Assignment stream: raw or first-difference IDs, exact zstd round trip.
    ib=ids.astype('<u2').tobytes(); di=ids.astype(np.int32); di[1:]-=ids[:-1]
    ims=[('u16',ZC.compress(ib)),('delta_i32',ZC.compress(di.astype('<i4').tobytes()))]; imode,ibb=min(ims,key=lambda z:len(z[1]))
    return q,ids,np.asarray(sizes),{'fixed_point_Q':Q,'layout':layout,'codebook_bytes':cb,'id_mode':imode,'id_bytes':len(ibb),'maxerr':me,'raw_codebook_i32_bytes':int(qi.nbytes),'raw_id_u16_bytes':len(ib)}


def entropy_bits(ids):
    _,cnt=np.unique(ids,return_counts=True); p=cnt/cnt.sum(); return float(-np.sum(cnt*np.log2(p)))


def raw_graph(V,eps):
    pairs=cKDTree(V,compact_nodes=True,balanced_tree=True).query_pairs(r=2*eps,p=np.inf,output_type='ndarray')
    G=nx.Graph();G.add_nodes_from(range(len(V)));G.add_edges_from((int(i),int(j)) for i,j in pairs);return G,pairs


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps); TV,TF,TY=s.gather_train(X,R0,co); V,F=s.gather_held(X,R0,co,eps)
    w,sl,sh,scale_bytes=a.fit_scale_model(TF,TY); sc=a.scales(F,w,sl,sh)
    lo,hi,rlo,rhi=exact_intervals(V,sc,eps)
    G,edges,searchr=graph_from_boxes(lo,hi); cl,maxcomp=clique_partition(G); q,ids,sz,packed=codewords_for_clusters(cl,lo,hi,V,sc,eps)
    deg=np.asarray([G.degree(i) for i in range(len(V))]); matching=nx.algorithms.matching.max_weight_matching(G,maxcardinality=True)
    RG,rpairs=raw_graph(V,eps); rdeg=np.asarray([RG.degree(i) for i in range(len(V))])
    N=len(V); nsamp=N*L; ideal=entropy_bits(ids); frame=128; paid=scale_bytes+packed['codebook_bytes']+packed['id_bytes']+frame; paidbps=8*paid/nsamp
    szb=g.szrun(X[g.TARGET_CH,g.TRAIN:g.END],eps); szbps=8*szb[0]/nsamp; target=szbps/2
    out={'global_std':std,'eps':eps,'ar_order':g.P,'block_length':L,'heldout_blocks':N,'heldout_samples':nsamp,
         'raw_box_graph':{'edges':int(len(rpairs)),'fraction_nonisolated':float(np.mean(rdeg>0)),'max_degree':int(np.max(rdeg))},
         'state_normalized_box_graph':{'candidate_search_radius':searchr,'edges':int(len(edges)),'fraction_nonisolated':float(np.mean(deg>0)),'max_degree':int(np.max(deg)),'connected_components':int(nx.number_connected_components(G)),'largest_component':int(maxcomp),'maximum_matching_edges':int(len(matching))},
         'constructive_clique_cover':{'clusters':int(len(cl)),'blocks_saved_vs_singletons':int(N-len(cl)),'largest_cluster':int(np.max(sz)),'fraction_blocks_in_multiblock_clusters':float(np.sum(sz[sz>1])/N),'cluster_size_counts':{str(k):int(np.sum(sz==k)) for k in np.unique(sz)},'free_codebook_empirical_id_bits':ideal,'free_codebook_empirical_id_bps':ideal/nsamp},
         'paid_target_trained_codebook':{**packed,'scale_model_bytes':scale_bytes,'framing_bytes':frame,'total_bytes_excluding_ar_prefix':int(paid),'bps_excluding_ar_prefix':paidbps},
         'matched_sz3_bps':szbps,'two_x_target_bps':target,'paid_bps_over_2x_target':paidbps/target,
         'scope':'Target-trained 8-D hard-box clique-cover ceiling/constructive diagnostic, NOT a sequential codec claim. The held-out hard residual blocks are given to the encoder to construct the cover. Each block becomes an exact interval box in normalized-codeword space under the decoder-known PR350 scale. Two boxes share a possible normalized reconstruction iff their intervals intersect. Axis-aligned boxes have the Helly property: a pairwise-intersecting clique has one common codeword. The exact sparse intersection graph is built and partitioned constructively into cliques via DSATUR coloring of each component complement. Each clique receives the midpoint of its common intersection; a fixed-point normalized codeword table and the complete assignment-ID stream are actually Zstd serialized and charged, and every assigned target residual is integer replayed under the unchanged epsilon. Because target AR state is held to the incumbent trajectory, even a good result would require a sequential follow-up; a poor result strongly rejects short state-normalized target-trained vector codebooks. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_normalized_box_clique_cover.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
