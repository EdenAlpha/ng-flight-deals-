import sys
import imperial_ar32_conditional_bitplane_rank as c

# Same codec and accounting as PR #506; only object width and public candidate partitions change.
c.C=128
c.h.PARTS=((128,4096),(128,2048),(128,1024),(64,2048),(64,1024),(32,4096),(32,2048),(32,1024),(32,512),(16,1024),(16,512),(8,1024),(8,512))

if __name__=='__main__':
    c.main(sys.argv[1])
