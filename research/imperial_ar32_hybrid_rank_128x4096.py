import sys
import imperial_ar32_hybrid_bitplane_rank as h
import imperial_ar32_hybrid_bitplane_rank_v2  # decoder fix only

h.C=128
h.PARTS=((128,4096),(128,2048),(128,1024),(64,2048),(64,1024),(32,4096),(32,2048),(32,1024),(32,512),(16,1024),(16,512),(8,1024),(8,512))

if __name__=='__main__':
    h.main(sys.argv[1])
