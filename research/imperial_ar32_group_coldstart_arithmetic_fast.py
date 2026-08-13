import sys
import imperial_ar32_channel_prev_arithmetic as a
import imperial_ar32_group_context_arithmetic_fast as g
import imperial_ar32_coldstart_arithmetic_fast as c

def ctxid_no_diag(mode,ch,prev,left,bitpos,prefix2,nb):
 return g.ctxid(mode,ch,prev,left,0,bitpos,prefix2,nb)
a.nctx=g.nctx
a.ctxid=ctxid_no_diag
c.MODES=('g16_prev4_leftsign','g8_prev4_leftsign','g32_prev4_left4','g16_prev4_left4')
if __name__=='__main__':c.main(sys.argv[1])
