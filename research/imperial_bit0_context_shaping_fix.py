import sys,numpy as np
import imperial_bit0_context_shaping as x
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m

def group_map_fixed(D,family):
    U=m.zig(np.asarray(D,np.int32)).astype(np.uint64)
    known=U & np.uint64(0xFFFFFFFFFFFFFFFE)
    keys=rr.context_keys(known,0,family)
    _,inv=np.unique(keys,return_inverse=True)
    gid=inv.reshape(D.shape).astype(np.int32)
    ng=int(inv.max())+1 if inv.size else 0
    gn=np.bincount(inv,minlength=ng).astype(np.int32)
    bits=(U.ravel()&1).astype(np.int32)
    gk=np.bincount(inv,weights=bits,minlength=ng).astype(np.int32)
    return gid,gn,gk

x.group_map=group_map_fixed
if __name__=='__main__':x.main(sys.argv[1])
