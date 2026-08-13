import json,sys
_real=json.dumps
def _dumps(obj,*args,**kwargs):
 kwargs.pop('flush',None)
 return _real(obj,*args,**kwargs)
json.dumps=_dumps
import imperial_daspack_matched_benchmark as a
if __name__=='__main__':a.main(sys.argv[1])
