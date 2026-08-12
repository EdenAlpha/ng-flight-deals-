import struct,sys
import soda_record_standalone as base

# The standalone header codec originally reused the global name HHS, which is
# also the imported PR #161 main-stream header size used by decode_main().
# Preserve the standalone value normally and temporarily restore the PR #161
# value only while its decoder executes.  No codec bytes or parameters change.
_pr161_decode_main=base.decode_main
_pr161_hhs=struct.calcsize(base.HHDR)

def decode_main_compat(blob):
    old=base.HHS
    base.HHS=_pr161_hhs
    try:
        return _pr161_decode_main(blob)
    finally:
        base.HHS=old

base.decode_main=decode_main_compat

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    base.main(sys.argv[1],sys.argv[2],sys.argv[3])
