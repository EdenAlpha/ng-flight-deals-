import sys,json,numpy as np
import imperial_ar32_linf_additive_cover as q
q.b.END=3072
q.b.TARGET_CH=np.asarray([0,32,64,96],dtype=np.int64)
q.b.N3S=(64,256)
if __name__=='__main__':
    q.b.main(sys.argv[1])
    p='imperial_ar32_additive_block_cover.json';d=json.load(open(p));d['codebook_training_geometry']='three-stage deterministic L-infinity k-center / bounding-box-midrange refinement';d['training_stage_stats']=q.TRAIN_STATS;d['fast_gate']=True;json.dump(d,open('imperial_ar32_linf_additive_fastgate.json','w'),indent=2)
