import struct,sys
import soda_record_standalone as base

# The standalone wrapper composes several older research modules that were
# originally executed into one globals() namespace.  Two independent codecs
# both used the short names HHS/SHS for their own header sizes.  Preserve the
# standalone values normally and temporarily restore each imported decoder's
# own size only while that decoder executes.  No encoded bytes, epsilon, or
# representation parameters change.
_pr161_decode_main=base.decode_main
_pr161_hhs=struct.calcsize(base.HHDR)
_sparse_decode_out=base.decode_out_sparse
_sparse_shs=struct.calcsize(base.SH)

def decode_main_compat(blob):
    old=base.HHS
    base.HHS=_pr161_hhs
    try:
        return _pr161_decode_main(blob)
    finally:
        base.HHS=old

def decode_out_sparse_compat(blob):
    old=base.SHS
    base.SHS=_sparse_shs
    try:
        return _sparse_decode_out(blob)
    finally:
        base.SHS=old

base.decode_main=decode_main_compat
base.decode_out_sparse=decode_out_sparse_compat

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    base.main(sys.argv[1],sys.argv[2],sys.argv[3])
