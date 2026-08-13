import imperial_local_hardbox_arithmetic as a
import sys
# Four of the lowest-local-std 128-channel blocks from the full-cable audit.
a.SPECS=(('quietest',1280),('quiet2',1792),('quiet3',2048),('quiet4',2560))
if __name__=='__main__':a.main(sys.argv[1])
