import sys
import imperial_ar32_innovation_feedback as a
a.SPECS=(('hard',512),)
a.NT=4096
a.ORDERS=(1,2,4,8,16)
if __name__=='__main__':a.main(sys.argv[1])
