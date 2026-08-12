import sys
import imperial_sparsest_legal_lorenzo_surface as m

# Same experiment, only enlarge the spatial patch so pysz's internal output
# buffer is safely above its tiny-array format overhead. Keep four fixed cable
# regimes so the MILP remains tractable. This commit intentionally retriggers
# CI after the original tiny-patch run executed before this wrapper was active.
m.NC=32
m.NT=64
m.SPECS=(
    ('hard',14464,512),
    ('easy',14464,2304),
    ('medium',14464,4608),
    ('far',14464,6880),
)

if __name__=='__main__':
    m.main(sys.argv[1])