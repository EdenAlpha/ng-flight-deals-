#!/usr/bin/env python3
"""Loader for the complete AXIOM JSG6 causal JSON research engine.

The canonical human-readable source is included in AXIOM_BEAST_V08.zip. The GitHub
connector used for this checkpoint has a practical large-text transport limit, so the
same source bytes are stored beside this loader as gzip+base64 and executed as the
module body. This is a source-transport workaround, not part of the AXIOM archive format.
"""
import os,base64,gzip
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'json_graph_transform_v6.py.gz.b64')
_src=gzip.decompress(base64.b64decode(open(_p,'rb').read()))
exec(compile(_src,'json_graph_transform_v6.py','exec'),globals(),globals())
