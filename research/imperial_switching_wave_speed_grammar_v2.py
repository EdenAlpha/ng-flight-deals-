import sys
import numpy as np
import imperial_switching_wave_speed_grammar as m

def legal_fixed(X,eps):
    bd=eps*m.SAFETY
    h=bd
    phi=m.PHASE_FRAC*h
    lo=np.ceil((X-bd-phi)/h-1e-12).astype(np.int32)
    hi=np.floor((X+bd-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):
        raise RuntimeError('empty legal')
    q=np.rint((X-phi)/h).astype(np.int32)
    q=np.minimum(np.maximum(q,lo),hi)
    return lo,hi,q,h,phi

m.legal=legal_fixed

if __name__=='__main__':
    m.main(sys.argv[1])
