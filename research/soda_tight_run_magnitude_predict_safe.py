import sys

# Execute the predictor definitions without its CLI in one namespace.
ns={'__builtins__':__builtins__,'__name__':'tight_mag_predict'}
src=open('research/soda_tight_run_magnitude_predict.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_run_magnitude_predict.py','exec'),ns,ns)

# The predictor defines its own HDR symbol. Historical event-gap outlier helpers
# also use a global HDR at call time, so isolate those helpers in a separate
# module namespace rather than allowing the symbols to collide. Codec logic and
# bytes are unchanged.
out={'__builtins__':__builtins__,'__name__':'outlier_codec'}
s2=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(s2,'soda_intergap_backend_hybrid.py','exec'),out,out)
ns['best_out']=out['best_out']
def decode_outlier_safe(bo,Oshape):
    if bo[1]=='gap':
        A=out['decode'](bo[6]).reshape(Oshape);return out['undelta'](A,1) if bo[2] else A
    A=out['decode_out_sparse'](bo[6]);return out['undelta'](A,1) if bo[2] else A
ns['decode_outlier']=decode_outlier_safe

ns['main'](sys.argv[1],float(sys.argv[2]))
