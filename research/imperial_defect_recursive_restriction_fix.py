import sys,numpy as np
import imperial_defect_recursive_restriction as r
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m


def decode_plane_fixed(payload,known,bit,shape):
    import struct
    off=0
    magic,ncmd,tm,cm,tlen,clen,nbits=struct.unpack_from('<4sHBBIII',payload,off);off+=20
    am,alen=struct.unpack_from('<BI',payload,off);off+=5
    if magic!=b'RRP1':raise RuntimeError('plane magic')
    tstore=payload[off:off+tlen];off+=tlen
    cstore=payload[off:off+clen];off+=clen
    astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError('plane trailing')
    traw=m.D.decompress(tstore) if tm else tstore
    craw=m.D.decompress(cstore) if cm else cstore
    araw=m.D.decompress(astore) if am else astore
    cmds=r.unpack_cmds(traw,ncmd);pos=[0]
    tree=r.rebuild_tree(cmds,pos,(0,shape[0],0,shape[1]))
    if pos[0]!=len(cmds):raise RuntimeError('unused tree')
    leaves=[];dummy=[];r.tree_commands(tree,dummy,leaves)
    ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);cp=0
    dummyB=np.zeros(shape,np.uint8)
    for box in leaves:
        c0,c1,t0,t1=box
        sub=np.zeros((c1-c0,t1-t0),np.uint8)
        flat=sub.ravel()
        for idx,n,_ in r.region_groups(dummyB,known,bit,box):
            k,cp=rr.get_uvar(craw,cp)
            if k>n:raise RuntimeError(('count',k,n))
            rn=n;rk=int(k)
            for local in idx:
                if rk==0:b=0
                elif rk==rn:b=1
                else:b=ad.decode(rn-rk,rk)
                flat[int(local)]=b
                rn-=1;rk-=b
            if rk:raise RuntimeError('rank remainder')
        B[c0:c1,t0:t1]=sub
    if cp!=len(craw):raise RuntimeError(('count trailing',cp,len(craw)))
    return B

r.decode_plane=decode_plane_fixed
if __name__=='__main__':r.main(sys.argv[1])
