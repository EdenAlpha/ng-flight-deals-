import sys,struct,numpy as np
import imperial_adaptive_gps_bit_questions as q
import imperial_decoder_phase_automaton as m


def adaptive_frame_fixed(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());remaining=list(range(nb));state=np.zeros(A.shape,np.uint16);last=np.zeros(A.shape,np.uint8)
    out=bytearray(struct.pack('<4sHHB',b'AGP1',A.shape[0],A.shape[1],nb));detail=[]
    for stage in range(nb):
        best=None
        for bit in remaining:
            B=((u>>bit)&1).astype(np.uint8)
            for fid in range(len(q.FAMILIES)):
                payload,d=q.encode_candidate(B,state,last,bit,fid);score=len(payload)
                if best is None or score<best[0]:best=(score,payload,d,B,bit)
        _,payload,d,B,bit=best
        out.extend(struct.pack('<I',len(payload)));out.extend(payload);detail.append({'stage':stage,**d});remaining.remove(bit);state=((state<<1)|B.astype(np.uint16));last=B
    buf=bytes(out);magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0);off=9
    if magic!=b'AGP1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('adaptive header')
    state=np.zeros(A.shape,np.uint16);last=np.zeros(A.shape,np.uint8);uu=np.zeros(A.shape,np.uint64);seen=set()
    for stage in range(nb):
        L=struct.unpack_from('<I',buf,off)[0];off+=4;payload=buf[off:off+L];off+=L;bit,B=q.decode_candidate(payload,state,last,A.shape)
        if bit in seen or bit<0 or bit>=nb:raise RuntimeError(('bit order',bit))
        seen.add(bit)
        uu|=B.astype(np.uint64)<<bit;state=((state<<1)|B.astype(np.uint16));last=B
    if off!=len(buf) or len(seen)!=nb:raise RuntimeError('adaptive trailing/order')
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('adaptive replay')
    return len(buf),'adaptive_gps_questions',Ad,detail

q.adaptive_frame=adaptive_frame_fixed
if __name__=='__main__':q.main(sys.argv[1])
