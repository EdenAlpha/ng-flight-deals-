# Small execution wrapper fixing one control-flow typo in the experimental
# driver before execution. The codec/state-selection functions and byte format
# in soda_tight_parity_aware_minchange.py are otherwise unchanged.
src=open('research/soda_tight_parity_aware_minchange.py').read()
old="if not r['valid']:raise RuntimeError(('parity-aware hard error',w,r['maxerr'],public_eps));rows.append(r)"
new="if not r['valid']:\n            raise RuntimeError(('parity-aware hard error',w,r['maxerr'],public_eps))\n        rows.append(r)"
if old not in src:raise RuntimeError('expected parity-aware driver typo not found')
src=src.replace(old,new,1)
exec(compile(src,'soda_tight_parity_aware_minchange.py','exec'),globals(),globals())
