import sys,numpy as np
import imperial_ar32_hybrid_bitplane_rank as h

# Patch only the decoder parser-state bug from v1. All coding/search logic is unchanged.
def decode_hybrid_fixed(container):
    raw=h.m.D.decompress(container[1:]) if container[0]==1 else bytes(container[1:])
    if raw[:4]!=h.MAGIC:raise RuntimeError('hybrid magic')
    pos=4;Cc,pos=h.read_uvar(raw,pos);Tt,pos=h.read_uvar(raw,pos);nb,pos=h.read_uvar(raw,pos);u=np.zeros((Cc,Tt),np.uint64)
    for bit in range(nb):
        if pos>=len(raw):raise RuntimeError(('plane tag eof',bit,pos,len(raw)))
        mode=raw[pos];pos+=1;flen,pos=h.read_uvar(raw,pos);end=pos+flen
        if end>len(raw):raise RuntimeError(('plane frame eof',bit,pos,flen,len(raw)))
        if mode==0:
            bl,pos2=h.read_uvar(raw,pos);z=raw[pos2:pos2+bl]
            if pos2+bl!=end:raise RuntimeError(('zstd frame length',bit,pos2+bl,end))
            bb=h.m.D.decompress(z);bits=np.unpackbits(np.frombuffer(bb,np.uint8),bitorder='little')[:Cc*Tt].reshape(Cc,Tt).astype(np.uint8)
        else:
            if mode<1 or mode>len(h.PARTS):raise RuntimeError(('plane mode',bit,mode,pos,end))
            cb,tb=h.PARTS[mode-1];bits,p2=h.enum_partition_decode(raw,pos,(Cc,Tt),cb,tb)
            if p2!=end:raise RuntimeError(('enum frame length',bit,mode,p2,end))
        pos=end
        u|=bits.astype(np.uint64)<<bit
    if pos!=len(raw):raise RuntimeError(('hybrid trailing',pos,len(raw)))
    return h.m.unzig(u).reshape(Cc,Tt)

h.decode_hybrid=decode_hybrid_fixed

if __name__=='__main__':
    h.main(sys.argv[1])
