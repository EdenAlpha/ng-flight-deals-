#!/usr/bin/env python3
"""Corrected framing shim for the exact spatial 5/3 lifting codec."""
import struct
import migrated_volume_3d_spatial_lifting as base

# y0,y1,x0,x1,level are uint32; kind and entropy-packer id are uint8;
# payload length is uint32. The initial prototype descriptor omitted pid.
base.BHDR='<IIIIIBBI'
base.BHSZ=struct.calcsize(base.BHDR)

compete=base.compete
decode=base.decode
encode_config=base.encode_config
sanity=base.sanity
hard=base.hard
