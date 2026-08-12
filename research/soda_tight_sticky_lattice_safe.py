import sys

# Execute the sticky-lattice definitions without invoking its CLI.
ns={'__builtins__':__builtins__,'__name__':'sticky_lattice'}
src=open('research/soda_tight_sticky_lattice.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_sticky_lattice.py','exec'),ns,ns)

# The sticky experiment intentionally defines its own SHS top-header size.
# Historical sparse-outlier helpers also read SHS dynamically, so isolate all
# outlier encode/decode helpers in a separate module namespace. Algorithm and
# serialized bytes are otherwise unchanged.
out={'__builtins__':__builtins__,'__name__':'outlier_codec'}
s2=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(s2,'soda_intergap_backend_hybrid.py','exec'),out,out)
ns['best_out']=out['best_out']

def decode_outlier_safe(bo,Oshape):
    if bo[1]=='gap':
        A=out['decode'](bo[6]).reshape(Oshape)
        return out['undelta'](A,1) if bo[2] else A
    A=out['decode_out_sparse'](bo[6])
    return out['undelta'](A,1) if bo[2] else A
ns['decode_outlier']=decode_outlier_safe
ns['decode_out_sparse']=out['decode_out_sparse']

ns['main'](sys.argv[1],float(sys.argv[2]))
