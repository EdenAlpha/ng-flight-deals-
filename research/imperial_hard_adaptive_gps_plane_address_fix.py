import sys,struct,numpy as np
import imperial_hard_adaptive_gps_plane_address as a
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m


def decode_rank_payload_fixed(payload,known,bit,shape):
    off=0
    fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',payload,off);off+=15
    cstore=payload[off:off+clen];off+=clen
    astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError('rank payload trailing')
    craw=m.D.decompress(cstore) if cm else cstore
    araw=m.D.decompress(astore) if am else astore
    keys=rr.context_keys(known,bit,rr.FAMILIES[fid])
    order,starts,ends=rr.groups_for(keys)
    ks=[];p=0
    for x,z in zip(starts,ends):
        k,p=rr.get_uvar(craw,p);n=int(z-x)
        if k>n:raise RuntimeError(('rank count',bit,k,n))
        ks.append(int(k))
    if p!=len(craw):raise RuntimeError(('rank count trailing',bit,p,len(craw)))
    ad=rr.ArithDecoder(araw,nbits)
    sorted_bits=np.empty(int(np.prod(shape)),np.uint8)
    for x,z,k in zip(starts,ends,ks):
        rn=int(z-x);rk=int(k)
        for j in range(int(x),int(z)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk!=0:raise RuntimeError(('rank remainder',bit,rk))
    flat=np.empty(int(np.prod(shape)),np.uint8);flat[order]=sorted_bits
    return flat.reshape(shape)


a.decode_rank_payload=decode_rank_payload_fixed
if __name__=='__main__':a.main(sys.argv[1])
