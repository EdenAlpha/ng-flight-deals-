import sys
import imperial_256lane_interrogator_topology_fast as f

# 1024 training samples + 1024 held-out samples. All transforms and exact byte
# accounting stay identical; only the time extent is shortened for a fast
# directional decision while PR #374 runs the full 8192-sample sweep.
f.q.NT=2048

if __name__=='__main__':f.q.main(sys.argv[1])
