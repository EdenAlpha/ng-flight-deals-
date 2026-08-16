import sys
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc

q.f.q_decode=sc.q_decode
if __name__=='__main__':q.main(sys.argv[1])
