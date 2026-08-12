import sys
import imperial_sparse_causal_annihilator as m
import imperial_sparse_causal_annihilator_jit as j
m.REGIONS=(('hard',512),)
m.encode_model=j.encode_model_jit
if __name__=='__main__': m.main(sys.argv[1])
