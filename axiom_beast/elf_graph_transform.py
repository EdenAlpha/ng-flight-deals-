#!/usr/bin/env python3
import os,re,struct,subprocess,hashlib

MAGIC=b'ELG1'
SPECIAL={'.dynsym':24,'.rela.dyn':24,'.rela.plt':24,'.gnu.version':2,'.got':8}

def vi(n):
    o=bytearray()
    while n>=128:o.append((n&127)|128);n>>=7
    o.append(n);return bytes(o)
def uv(b,p):
    n=s=0
    while True:
        if p>=len(b):raise ValueError('varint')
        x=b[p];p+=1;n|=(x&127)<<s
        if x<128:return n,p
        s+=7
        if s>70:raise ValueError('varint overflow')
def svi(n):return vi(n*2 if n>=0 else -n*2-1)
def usv(b,p):
    z,p=uv(b,p);return (z//2 if z%2==0 else -(z//2)-1),p

def _elf_sections(d):
    if len(d)<64 or d[:4]!=b'\x7fELF' or d[4]!=2 or d[5]!=1:return None
    shoff=struct.unpack_from('<Q',d,0x28)[0];shents=struct.unpack_from('<H',d,0x3A)[0];shnum=struct.unpack_from('<H',d,0x3C)[0];shstr=struct.unpack_from('<H',d,0x3E)[0]
    if shents<64 or shnum==0 or shoff+shents*shnum>len(d) or shstr>=shnum:return None
    ss=[]
    for i in range(shnum):
        o=shoff+i*shents;x=struct.unpack_from('<IIQQQQIIQQ',d,o)
        ss.append({'i':i,'nameoff':x[0],'type':x[1],'flags':x[2],'addr':x[3],'off':x[4],'size':x[5],'link':x[6],'info':x[7],'align':x[8],'entsize':x[9]})
    s=ss[shstr]
    if s['off']+s['size']>len(d):return None
    st=d[s['off']:s['off']+s['size']]
    for x in ss:
        no=x['nameoff'];e=st.find(b'\0',no) if no<len(st) else -1
        x['name']=st[no:e].decode('latin1') if e>=0 else ''
    return ss

def _branch(a,b):
    if len(b)>=5 and b[0] in (0xE8,0xE9):pos,w=1,4
    elif len(b)>=6 and b[0]==0x0F and 0x80<=b[1]<=0x8F:pos,w=2,4
    elif len(b)>=2 and (b[0]==0xEB or 0x70<=b[0]<=0x7F or 0xE0<=b[0]<=0xE3):pos,w=1,1
    else:return None
    disp=int.from_bytes(b[pos:pos+w],'little',signed=True)
    return pos,w,a+len(b)+disp

def _transpose(b,rec):
    if rec<=0 or len(b)%rec:raise ValueError('record')
    n=len(b)//rec
    return b''.join(bytes(b[i*rec+j] for i in range(n)) for j in range(rec))
def _untranspose(b,rec):
    if rec<=0 or len(b)%rec:raise ValueError('record')
    n=len(b)//rec;o=bytearray(len(b))
    p=0
    for j in range(rec):
        col=b[p:p+n];p+=n
        for i,x in enumerate(col):o[i*rec+j]=x
    return bytes(o)

def _special_pack(name,b):
    if name=='.eh_frame_hdr' and len(b)>=12 and (len(b)-12)%8==0:return 2,b[:12]+_transpose(b[12:],8)
    rec=SPECIAL.get(name)
    if rec and len(b)%rec==0:return 1,_transpose(b,rec)
    return None

def _special_unpack(name,code,b):
    if code==2:
        if name!='.eh_frame_hdr' or len(b)<12:return None
        return b[:12]+_untranspose(b[12:],8)
    if code==1:
        rec=SPECIAL.get(name)
        if not rec:return None
        return _untranspose(b,rec)
    return None

def pack(data):
    ss=_elf_sections(data)
    if not ss:return None
    text=next((x for x in ss if x['name']=='.text' and x['size']>1024 and x['off']+x['size']<=len(data)),None)
    if not text:return None
    # GNU objdump is compression-side only; the archive decoder needs no disassembler.
    import tempfile
    tf=tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(data);tf.close()
        od=subprocess.check_output(['objdump','-d','-z','-w','--section=.text','--insn-width=16',tf.name],text=True,errors='replace')
    except Exception:
        try:os.unlink(tf.name)
        except Exception:pass
        return None
    finally:
        try:os.unlink(tf.name)
        except Exception:pass
    pat=re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(\S+)?')
    ins=[]
    for line in od.splitlines():
        m=pat.match(line)
        if not m:continue
        a=int(m.group(1),16);bb=bytes.fromhex(m.group(2));mn=m.group(3) or ''
        if text['addr']<=a<text['addr']+text['size']:ins.append([a,bb,mn,line])
    ins.sort(key=lambda z:z[0])
    rawtext=data[text['off']:text['off']+text['size']]
    if not ins or b''.join(x[1] for x in ins)!=rawtext:return None
    # Discover RIP-relative displacement position from objdump's resolved target comment.
    rip={}
    for i,(a,bb,mn,line) in enumerate(ins):
        if '%rip' not in line:continue
        m=re.search(r'#\s*([0-9a-fA-F]+)',line)
        if not m:continue
        targ=int(m.group(1),16);disp=targ-(a+len(bb))
        if not (-(1<<31)<=disp<(1<<31)):continue
        q=int(disp).to_bytes(4,'little',signed=True);poses=[j for j in range(len(bb)-3) if bb[j:j+4]==q]
        if len(poses)==1:rip[i]=(poses[0],targ)
    # Class = mnemonic/length plus the causal coordinate-field layout. Mnemonic is used only to form classes;
    # decoder stores only opaque class IDs + length/field metadata.
    keys=[]
    for i,(a,bb,mn,line) in enumerate(ins):
        br=_branch(a,bb);bp,bw=(br[0],br[1]) if br else (255,0);rp=rip[i][0] if i in rip else 255
        keys.append((mn,len(bb),bp,bw,rp))
    from collections import Counter
    cnt=Counter(keys);order=[k for k,n in cnt.most_common()];kid={k:i for i,k in enumerate(order)}
    # Variable-width frequency IDs.
    ids=b''.join(vi(kid[k]) for k in keys)
    groups={k:[] for k in order};branch_targets=[];rip_targets=[]
    addr_to_i={a:i for i,(a,bb,mn,line) in enumerate(ins)}
    for i,(a,bb,mn,line) in enumerate(ins):
        k=keys[i];z=bytearray(bb);br=_branch(a,bb)
        if br:
            bp,bw,t=br;z[bp:bp+bw]=b'\0'*bw
            if t in addr_to_i:
                dd=addr_to_i[t]-i;zz=dd*2 if dd>=0 else -dd*2-1;branch_targets.append(zz<<1)
            else:
                rel=t-text['addr'];zz=rel*2 if rel>=0 else -rel*2-1;branch_targets.append((zz<<1)|1)
        if i in rip:
            rp,t=rip[i];z[rp:rp+4]=b'\0'*4;rip_targets.append(t-text['addr'])
        groups[k].append(bytes(z))
    body=bytearray()
    for k in order:
        xs=groups[k];L=k[1]
        for j in range(L):body+=bytes(x[j] for x in xs)
    bstream=b''.join(vi(x) for x in branch_targets)
    uniq=sorted(set(rip_targets));rmap={x:i for i,x in enumerate(uniq)};rdict=bytearray();prev=0
    for x in uniq:rdict+=svi(x-prev);prev=x
    rids=b''.join(vi(rmap[x]) for x in rip_targets)
    # Skeleton removes text and only special sections whose reversible transposition is accepted.
    sk=bytearray(data);sk[text['off']:text['off']+text['size']]=b'\0'*text['size'];special=[]
    for x in ss:
        if x['off']+x['size']>len(data) or x['size']==0 or x['name']=='.text':continue
        q=_special_pack(x['name'],data[x['off']:x['off']+x['size']])
        if q:
            code,rep=q;sk[x['off']:x['off']+x['size']]=b'\0'*x['size'];special.append((x['name'],code,rep))
    o=bytearray(MAGIC)+vi(len(data))+hashlib.sha256(data).digest()+vi(len(sk))+sk
    o+=vi(len(order))
    for mn,L,bp,bw,rp in order:o+=bytes([L,bp,bw,rp])
    o+=vi(len(ins))+vi(len(ids))+ids+vi(len(body))+body
    o+=vi(len(branch_targets))+vi(len(bstream))+bstream
    o+=vi(len(uniq))+vi(len(rdict))+rdict+vi(len(rids))+rids
    o+=vi(len(special))
    for name,code,rep in special:
        nb=name.encode('latin1');o+=vi(len(nb))+nb+bytes([code])+vi(len(rep))+rep
    rep=bytes(o)
    return rep if unpack(rep)==data else None

def unpack(rep):
    if rep[:4]!=MAGIC:raise ValueError('ELG magic')
    p=4;orig,p=uv(rep,p);digest=rep[p:p+32];p+=32;sl,p=uv(rep,p);sk=bytearray(rep[p:p+sl]);p+=sl
    ss=_elf_sections(bytes(sk))
    if not ss:raise ValueError('ELG skeleton')
    text=next((x for x in ss if x['name']=='.text'),None)
    if not text:raise ValueError('ELG text')
    nc,p=uv(rep,p);meta=[]
    for _ in range(nc):
        if p+4>len(rep):raise ValueError('ELG class meta')
        L,bp,bw,rp=rep[p:p+4];p+=4;meta.append((L,bp,bw,rp))
    ni,p=uv(rep,p);il,p=uv(rep,p);ib=rep[p:p+il];p+=il
    ids=[];q=0
    for _ in range(ni):x,q=uv(ib,q);ids.append(x)
    if q!=len(ib) or any(x>=nc for x in ids):raise ValueError('ELG ids')
    bl,p=uv(rep,p);body=rep[p:p+bl];p+=bl
    if bl!=text['size']:raise ValueError('ELG text body')
    nb,p=uv(rep,p);bsl,p=uv(rep,p);bs=rep[p:p+bsl];p+=bsl
    bcodes=[];q=0
    for _ in range(nb):x,q=uv(bs,q);bcodes.append(x)
    if q!=len(bs):raise ValueError('ELG branch stream')
    nr,p=uv(rep,p);rdl,p=uv(rep,p);rdb=rep[p:p+rdl];p+=rdl
    rvals=[];q=0;prev=0
    for _ in range(nr):dd,q=usv(rdb,q);prev+=dd;rvals.append(prev)
    if q!=len(rdb):raise ValueError('ELG rip dict')
    ril,p=uv(rep,p);rib=rep[p:p+ril];p+=ril
    # number of RIP refs follows from class sequence
    rip_count=sum(1 for cid in ids if meta[cid][3]!=255);rids=[];q=0
    for _ in range(rip_count):x,q=uv(rib,q);rids.append(x)
    if q!=len(rib) or any(x>=len(rvals) for x in rids):raise ValueError('ELG rip ids')
    # Decode grouped columns into zero-coordinate instruction bytes.
    counts=[0]*nc
    for cid in ids:counts[cid]+=1
    cols=[];q=0
    for cid,(L,bp,bw,rp) in enumerate(meta):
        cc=[];n=counts[cid]
        for _ in range(L):cc.append(body[q:q+n]);q+=n
        cols.append(cc)
    if q!=len(body):raise ValueError('ELG body parse')
    pos=[0]*nc;inst=[]
    for cid in ids:
        L=meta[cid][0];j=pos[cid];pos[cid]+=1;inst.append(bytearray(cols[cid][k][j] for k in range(L)))
    # Instruction addresses are determined entirely by lengths/class sequence.
    addrs=[];a=text['addr']
    for z in inst:addrs.append(a);a+=len(z)
    if a!=text['addr']+text['size']:raise ValueError('ELG address coverage')
    bi=ri=0
    for i,z in enumerate(inst):
        L,bp,bw,rp=meta[ids[i]]
        if bp!=255:
            if bi>=len(bcodes):raise ValueError('ELG branch count')
            code=bcodes[bi];bi+=1;zz=code>>1;val=zz//2 if zz%2==0 else -(zz//2)-1
            if code&1:
                target=text['addr']+val
            else:
                ti=i+val
                if ti<0 or ti>=len(inst):raise ValueError('ELG branch target')
                target=addrs[ti]
            disp=target-(addrs[i]+L)
            z[bp:bp+bw]=int(disp).to_bytes(bw,'little',signed=True)
        if rp!=255:
            if ri>=len(rids):raise ValueError('ELG rip count')
            target=text['addr']+rvals[rids[ri]];ri+=1;disp=target-(addrs[i]+L)
            z[rp:rp+4]=int(disp).to_bytes(4,'little',signed=True)
    if bi!=len(bcodes) or ri!=len(rids):raise ValueError('ELG coordinate counts')
    rawtext=b''.join(inst)
    if len(rawtext)!=text['size']:raise ValueError('ELG text length')
    sk[text['off']:text['off']+text['size']]=rawtext
    ns,p=uv(rep,p)
    # Reparse after text restoration; section headers never changed, but keeps logic simple.
    ss=_elf_sections(bytes(sk));byname={x['name']:x for x in ss}
    for _ in range(ns):
        nl,p=uv(rep,p);name=rep[p:p+nl].decode('latin1');p+=nl;code=rep[p];p+=1;rl,p=uv(rep,p);r=rep[p:p+rl];p+=rl
        x=byname.get(name)
        if not x or x['off']+x['size']>len(sk):raise ValueError('ELG special section')
        raw=_special_unpack(name,code,r)
        if raw is None or len(raw)!=x['size']:raise ValueError('ELG special decode')
        sk[x['off']:x['off']+x['size']]=raw
    if p!=len(rep):raise ValueError('ELG trailing')
    out=bytes(sk)
    if len(out)!=orig or hashlib.sha256(out).digest()!=digest:raise ValueError('ELG integrity')
    return out
