#!/usr/bin/env python3
import os,sys,struct,hashlib,lzma,subprocess
import numpy as np
import video_probe as V
import video_block_probe as B
import video_context_v2_probe as X
MAGIC=b'AXV1'; W,H,FPS=V.W,V.H,V.FPS

def cb(data):
    cand=[(1,lzma.compress(data,preset=9|lzma.PRESET_EXTREME))]
    try:
        q=subprocess.run(['brotli','-q','11','-c'],input=data,stdout=subprocess.PIPE,check=True).stdout;cand.append((2,q))
    except Exception:pass
    try:
        q=subprocess.run(['zstd','-22','--ultra','-q','-c'],input=data,stdout=subprocess.PIPE,check=True).stdout;cand.append((3,q))
    except Exception:pass
    return min(cand,key=lambda x:len(x[1]))
def db(cid,data):
    if cid==1:return lzma.decompress(data)
    if cid==2:return subprocess.run(['brotli','-d','-c'],input=data,stdout=subprocess.PIPE,check=True).stdout
    if cid==3:return subprocess.run(['zstd','-d','-q','-c'],input=data,stdout=subprocess.PIPE,check=True).stdout
    raise ValueError('codec')
def part(raw):
    cid,c=cb(raw);return bytes([cid])+struct.pack('<II',len(raw),len(c))+c
def unpart(b,p):
    cid=b[p];rl,cl=struct.unpack_from('<II',b,p+1);p+=9;q=db(cid,b[p:p+cl]);p+=cl
    if len(q)!=rl:raise ValueError('part length')
    return q,p

def pack_nibbles(a):
    n=len(a);z=np.zeros((n+1)//2,dtype=np.uint8)
    z[:n//2]=(a[0:2*(n//2):2]&15)|((a[1:2*(n//2):2]&15)<<4)
    if n&1:z[-1]=a[-1]&15
    return z.tobytes()
def unpack_nibbles(b,n):
    a=np.frombuffer(b,dtype=np.uint8);o=np.empty(n,dtype=np.uint8)
    o[0::2]=a[:(n+1)//2]&15
    if n>1:o[1::2]=(a[:n//2]>>4)&15
    return o

def packet_direct(raw):return b'\x00'+struct.pack('<I',len(raw))+part(raw)
def packet_sparse(raw,nibble=False):
    a=np.frombuffer(raw,dtype=np.uint8);mask=np.packbits((a!=0).astype(np.uint8),bitorder='little').tobytes();nz=a[a!=0]
    if not nibble:return b'\x01'+struct.pack('<I',len(a))+part(mask)+part(nz.tobytes())
    return b'\x02'+struct.pack('<II',len(a),len(nz))+part(mask)+part(pack_nibbles((nz>>4).astype(np.uint8)))+part(pack_nibbles((nz&15).astype(np.uint8)))
def packet_bitplanes(raw):
    a=np.frombuffer(raw,dtype=np.uint8);o=bytearray(b'\x03'+struct.pack('<I',len(a)))
    for bit in range(8):o+=part(np.packbits(((a>>bit)&1).astype(np.uint8),bitorder='little').tobytes())
    return bytes(o)
def bestpacket(raw):
    c=[packet_direct(raw),packet_sparse(raw,False),packet_bitplanes(raw)]
    if any(raw):c.append(packet_sparse(raw,True))
    return min(c,key=len)
def unpacket(b):
    if not b:return b''
    m=b[0];p=1
    if m==0:
        n=struct.unpack_from('<I',b,p)[0];p+=4;q,p=unpart(b,p);out=q
    elif m in (1,2):
        if m==1:n=struct.unpack_from('<I',b,p)[0];p+=4;nz_n=None
        else:n,nz_n=struct.unpack_from('<II',b,p);p+=8
        mask,p=unpart(b,p);bits=np.unpackbits(np.frombuffer(mask,dtype=np.uint8),bitorder='little')[:n].astype(bool);out=np.zeros(n,dtype=np.uint8)
        if m==1:nz,p=unpart(b,p);vals=np.frombuffer(nz,dtype=np.uint8)
        else:
            hi,p=unpart(b,p);lo,p=unpart(b,p);vals=((unpack_nibbles(hi,nz_n)<<4)|unpack_nibbles(lo,nz_n)).astype(np.uint8)
        out[bits]=vals;out=out.tobytes()
    elif m==3:
        n=struct.unpack_from('<I',b,p)[0];p+=4;out=np.zeros(n,dtype=np.uint8)
        for bit in range(8):
            q,p=unpart(b,p);v=np.unpackbits(np.frombuffer(q,dtype=np.uint8),bitorder='little')[:n];out|=(v.astype(np.uint8)<<bit)
        out=out.tobytes()
    else:raise ValueError('packet method')
    if p!=len(b):raise ValueError('packet trailing')
    return out

def put_blob(o,b):o+=struct.pack('<I',len(b))+b
def get_blob(b,p):
    n=struct.unpack_from('<I',b,p)[0];p+=4;return b[p:p+n],p+n

def pack_map(mode_bytes,nf,bpf):
    a=np.frombuffer(mode_bytes,dtype=np.uint8).reshape(nf,bpf);a0=packet_direct(mode_bytes);a1=packet_direct(a.T.tobytes())
    return (b'\x00'+a0) if len(a0)<=len(a1) else (b'\x01'+a1)
def unpack_map(blob,nf,bpf):
    layout=blob[0];q=unpacket(blob[1:])
    if layout==0:return q
    return np.frombuffer(q,dtype=np.uint8).reshape(bpf,nf).T.copy().tobytes()

def encode(raw):
    Y,U,Cc=V.split(raw);nf=len(Y);yr,ym,xd,yd=B.encode_y(Y);motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)];ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(Cc,8,motions,2)
    my=X.metas(nf,H,W,16);mc=X.metas(nf,H//2,W//2,8);ys,yg=X.split_mode(yr,ym,my);us,ug=X.split_mode(ur,um,mc);vs,vg=X.split_mode(vr,vm,mc)
    mx=bytes(xd[i] for i,m in enumerate(ym) if m==4);myv=bytes(yd[i] for i,m in enumerate(ym) if m==4)
    bpfy=((W+15)//16)*((H+15)//16);bpfc=((W//2+7)//8)*((H//2+7)//8)
    o=bytearray(MAGIC)+struct.pack('<HHHI',W,H,nf,len(raw))+hashlib.sha256(raw).digest()
    for q in (pack_map(ym,nf,bpfy),pack_map(um,nf,bpfc),pack_map(vm,nf,bpfc),packet_direct(mx),packet_direct(myv),packet_direct(bytes((x+16)&31 for x,y in motions)),packet_direct(bytes((y+16)&31 for x,y in motions))):put_blob(o,q)
    for ss in (ys,us,vs):
        for k in range(5):put_blob(o,bestpacket(ss.get(k,b'')) if k in ss else b'')
    return bytes(o)
def decode(blob):
    if blob[:4]!=MAGIC:raise ValueError('magic')
    p=4;w,h,nf,orig=struct.unpack_from('<HHHI',blob,p);p+=10;digest=blob[p:p+32];p+=32
    if (w,h)!=(W,H):raise ValueError('geometry')
    bpfy=((W+15)//16)*((H+15)//16);bpfc=((W//2+7)//8)*((H//2+7)//8)
    maps=[]
    for bpf in (bpfy,bpfc,bpfc):q,p=get_blob(blob,p);maps.append(unpack_map(q,nf,bpf))
    arr=[]
    for _ in range(4):q,p=get_blob(blob,p);arr.append(unpacket(q))
    mx,myv,gdx,gdy=arr;motions=[(gdx[i]-16,gdy[i]-16) for i in range(nf)]
    residual=[]
    for _plane in range(3):
        d={}
        for k in range(5):q,p=get_blob(blob,p);d[k]=unpacket(q) if q else b''
        residual.append(d)
    if p!=len(blob):raise ValueError('trailing')
    mymeta=X.metas(nf,H,W,16);mcmeta=X.metas(nf,H//2,W//2,8)
    streams=[]
    for d,m,meta,shape in ((residual[0],maps[0],mymeta,(nf,H,W)),(residual[1],maps[1],mcmeta,(nf,H//2,W//2)),(residual[2],maps[2],mcmeta,(nf,H//2,W//2))):
        groups={}
        for z in meta:groups.setdefault(m[z[0]],[]).append(z)
        clean={k:d[k] for k in groups};streams.append(X.unsplit(clean,groups,shape))
    ym,um,vm=maps;x2=bytearray([16])*len(ym);y2=bytearray([16])*len(ym);j=0
    for i,m in enumerate(ym):
        if m==4:x2[i]=mx[j];y2[i]=myv[j];j+=1
    raw=V.join((B.decode_y(streams[0],ym,bytes(x2),bytes(y2)),V.decode_plane(streams[1],um,8,motions,2),V.decode_plane(streams[2],vm,8,motions,2)))
    if len(raw)!=orig or hashlib.sha256(raw).digest()!=digest:raise ValueError('integrity')
    return raw

def main():
    if len(sys.argv)!=4 or sys.argv[1] not in ('c','d'):raise SystemExit('usage: video_context_archive.py c|d in out')
    if sys.argv[1]=='c':
        raw=open(sys.argv[2],'rb').read();q=encode(raw);open(sys.argv[3],'wb').write(q);print({'original':len(raw),'archive':len(q),'ratio':len(raw)/len(q)})
    else:
        q=open(sys.argv[2],'rb').read();raw=decode(q);open(sys.argv[3],'wb').write(raw);print({'output':len(raw)})
if __name__=='__main__':main()
