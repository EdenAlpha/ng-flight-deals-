#!/usr/bin/env python3
import migrated_volume_3d_codec as codec
import migrated_volume_3d_entropy as entropy
codec.pack=entropy.pack
codec.unpack=entropy.unpack
import migrated_volume_3d_adaptive_v2 as adaptive_v2
adaptive_v2.install()
import migrated_volume_3d_runner as runner
import migrated_volume_3d_geometry_v2 as geometry_v2

runner.SCAN=40000
runner.NY=4
_base_geometry_candidates=runner.geometry_candidates
runner.geometry_candidates=lambda A: geometry_v2.geometry_candidates(_base_geometry_candidates,runner,A)
_base_choose_geometry=runner.choose_geometry

# Structural width selection, never dataset-name routing. Prefer wider native
# spatial context, but fall back when SEG-Y header run geometry cannot support it.
def _choose_geometry_width_adaptive(A):
    errors=[]
    for nx in (64,48,32):
        runner.NX=nx
        try:
            q,ranked=_base_choose_geometry(A)
            ranked=[dict(x,selected_fast_width=nx) for x in ranked]
            q=dict(q); q['selected_fast_width']=nx
            return q,ranked
        except RuntimeError as e:
            errors.append((nx,repr(e)))
    raise RuntimeError(('no coherent spatial line segmentation at widths 64/48/32',errors))

runner.choose_geometry=_choose_geometry_width_adaptive

if __name__=='__main__':
    entropy.sanity()
    adaptive_v2.sanity()
    runner.main()
