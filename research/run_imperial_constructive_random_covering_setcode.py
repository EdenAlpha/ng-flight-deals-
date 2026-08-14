import sys
import numpy as np
import imperial_constructive_random_covering_setcode as q

_seedbase=q.seedbase
q.seedbase=lambda region_id,c,block: np.uint64(_seedbase(region_id,c,block))
q.main(sys.argv[1])
