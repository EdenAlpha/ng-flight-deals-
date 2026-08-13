import sys
import imperial_ar32_channel_prev_arithmetic as a
a.SPECS=(('hard',512),)
a.NT=4096
a.MODES=('channel_prev4','prev4_left4')
if __name__=='__main__':a.main(sys.argv[1])
