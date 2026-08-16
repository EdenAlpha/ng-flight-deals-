import sys
import imperial_near2eps_hybrid_predictor_zsm_fix as w
import imperial_near2eps_scale_128x4096 as sc

w.q.f.q_decode=sc.q_decode
w.q.z.f.q_decode=sc.q_decode
if __name__=='__main__':w.q.main(sys.argv[1])
