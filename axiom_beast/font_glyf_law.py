#!/usr/bin/env python3
from io import BytesIO
try:
    from fontTools.ttLib import TTFont
    from fontTools.ttLib.woff2 import WOFF2GlyfTable
except Exception:
    TTFont=WOFF2GlyfTable=None
from axiom3_common import vi,uv
MAGIC=b'FGL1'

def pack(d):
    if TTFont is None:return None
    try:
        f=TTFont(BytesIO(d),lazy=False,recalcTimestamp=False)
        if 'glyf' not in f or 'loca' not in f:return None
        e=f.reader.tables['glyf']
        g=WOFF2GlyfTable('glyf');g.glyphs=f['glyf'].glyphs;g.glyphOrder=f.getGlyphOrder()
        td=g.transform(f)
        if td is None:return None
        sk=bytearray(d);sk[e.offset:e.offset+e.length]=b'\0'*e.length
        rep=MAGIC+vi(e.offset)+vi(e.length)+vi(len(sk))+bytes(sk)+vi(len(td))+td
        return rep if unpack(rep)==d else None
    except Exception:
        return None

def unpack(rep):
    if TTFont is None:raise RuntimeError('fontTools required for TTF glyph-law decoding')
    if rep[:4]!=MAGIC:raise ValueError('font glyf law')
    p=4;off,p=uv(rep,p);ln,p=uv(rep,p);sl,p=uv(rep,p);sk=bytearray(rep[p:p+sl]);p+=sl;tl,p=uv(rep,p);td=rep[p:p+tl];p+=tl
    if p!=len(rep):raise ValueError('trailing font law')
    f=TTFont(BytesIO(bytes(sk)),lazy=True,recalcTimestamp=False)
    g=WOFF2GlyfTable('glyf');g.reconstruct(td,f);raw=g.compile(f)
    if len(raw)!=ln:raise ValueError('glyf length mismatch')
    sk[off:off+ln]=raw
    return bytes(sk)
