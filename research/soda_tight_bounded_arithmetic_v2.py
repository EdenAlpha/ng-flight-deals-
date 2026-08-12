import struct,sys

# Execute the exact PR #194 experiment definition without its CLI call, then
# correct only the container schema typo: there are five one-byte fields after
# the magic (version, order-code, dtype-code, cutoff, magnitude-Rice flag), not
# six.  All model/coder semantics and candidate cutoffs remain unchanged.
src=open('research/soda_tight_bounded_arithmetic.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_bounded_arithmetic.py','exec'),globals())
BA_HDR='<8sBBBBB4I12B12Q'
BA_HS=struct.calcsize(BA_HDR)
main(sys.argv[1],float(sys.argv[2]))
