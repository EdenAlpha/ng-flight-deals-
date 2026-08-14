import sys,traceback
import imperial_huber_ar32_trellis_quantizer as q

try:
    q.main(sys.argv[1])
except Exception:
    tb=traceback.format_exc()
    esc=tb.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    print(f'::error title=trellis gate traceback::{esc}',flush=True)
    with open('imperial_huber_ar32_trellis_error.txt','w') as f:f.write(tb)
    raise
