#!/usr/bin/env python3
import os, re, struct, subprocess, tempfile, shutil, hashlib, math, json
from collections import Counter, defaultdict
import numpy as np

ROOT=os.path.dirname(os.path.abspath(__file__))
D=os.path.join(ROOT,'data'); O=os.path.join(ROOT,'out'); os.makedirs(D,exist_ok=True); os.makedirs(O,exist_ok=True)

def sh(s): subprocess.run(['bash','-lc',s],check=True)
def fsize(p): return os.path.getsize(p)
def vi(n):
    o=bytearray()
    while n>=128:o.append((n&127)|128);n>>=7
    o.append(n);return bytes(o)
def uv(b,p):
    n=s=0
    while 1:
        x=b[p];p+=1;n|=(x&127)<<s
        if x<128:return n,p
        s+=7

def outer_sizes(name, raw, rep):
    td=tempfile.mkdtemp(); rp=os.path.join(td,'rep'); op=os.path.join(td,'raw')
    open(rp,'wb').write(rep);open(op,'wb').write(raw)
    vals={}
    for label,path in [('rep',rp),('raw',op)]:
        xz=path+'.xz'; br=path+'.br'; zst=path+'.zst'
        subprocess.run(['xz','-9e','-k','-f',path],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['zstd','-22','--ultra','-q','-f',path,'-o',zst],check=True)
        with open(br,'wb') as f: subprocess.run(['brotli','-q','11','-c',path],check=True,stdout=f)
        vals[label]={'xz':fsize(xz),'br':fsize(br),'zst':fsize(zst)}
    shutil.rmtree(td)
    rb=min(vals['raw'].values()); rr=min(vals['rep'].values());
    return {'raw_best':rb,'raw_codec':min(vals['raw'],key=vals['raw'].get),'rep_best':rr,'rep_codec':min(vals['rep'],key=vals['rep'].get),'gain_pct':round((rb-rr)*100/rb,2), 'all':vals}

TOK=re.compile(rb'[A-Za-z_][A-Za-z0-9_]*|\d+')

def dict_band(vals):
    c=Counter(vals); ds=[x for x,_ in sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))]; mp={x:i for i,x in enumerate(ds)}
    return vi(len(ds))+b''.join(vi(len(x))+x for x in ds)+b''.join(vi(mp[x]) for x in vals)
def undict(b,n):
    p=0;k,p=uv(b,p);ds=[]
    for _ in range(k):l,p=uv(b,p);ds.append(b[p:p+l]);p+=l
    out=[]
    for _ in range(n):i,p=uv(b,p);out.append(ds[i])
    if p!=len(b): raise ValueError('dict trailing')
    return out

def lex_pack(data):
    toks=[];seps=[];last=0
    for m in TOK.finditer(data): seps.append(data[last:m.start()]);toks.append(m.group());last=m.end()
    seps.append(data[last:])
    if len(toks)<16: return b'R'+data
    tb=dict_band(toks); sb=dict_band(seps)
    return b'L'+vi(len(toks))+vi(len(tb))+tb+sb

def lex_unpack(rep):
    if rep[:1]==b'R': return rep[1:]
    p=1;n,p=uv(rep,p);tl,p=uv(rep,p);toks=undict(rep[p:p+tl],n);p+=tl;seps=undict(rep[p:],n+1)
    o=bytearray(seps[0])
    for i,t in enumerate(toks):o+=t+seps[i+1]
    return bytes(o)

def parse_tar(raw):
    ents=[]; p=0
    while p+512<=len(raw):
        h=raw[p:p+512]
        if h==b'\0'*512:
            return ents,raw[p:]
        try:
            fld=h[124:136].rstrip(b'\0 ').strip() or b'0'; sz=int(fld,8)
        except: return None,None
        s=p+512;e=s+sz;pad=(-sz)%512
        if e+pad>len(raw):return None,None
        ents.append((h,raw[s:e],raw[e:e+pad]));p=e+pad
    return ents,raw[p:]

def is_text(name,data):
    ext=os.path.splitext(name.decode('utf-8','ignore'))[1].lower()
    if ext in {'.kt','.java','.xml','.gradle','.kts','.properties','.toml','.json','.txt','.md','.pro','.sh','.yml','.yaml','.c','.h','.cpp','.hpp','.py'}: return True
    if not data:return True
    s=data[:4096]; return b'\0' not in s and sum((c in b'\t\n\r' or 32<=c<127) for c in s)/len(s)>0.93

def tar_pack(raw):
    ents,tail=parse_tar(raw)
    if ents is None:return None
    headers=b''.join(e[0] for e in ents)
    meta=bytearray(b'TLB2')+vi(len(ents))+vi(len(headers))+headers
    text=[];binary=[]
    for h,d,pad in ents:
        name=h[:100].split(b'\0',1)[0]
        g=0 if is_text(name,d) else 1
        meta+=bytes([g])+vi(len(d))+vi(len(pad))
        if any(pad): meta+=b'1'+vi(len(pad))+pad
        else:meta+=b'0'
        (text if g==0 else binary).append(d)
    textcat=b''.join(text); lrep=lex_pack(textcat); bincat=b''.join(binary)
    meta+=vi(len(lrep))+lrep+vi(len(bincat))+bincat+vi(len(tail))+tail
    return bytes(meta)

def tar_unpack(rep):
    if rep[:4]!=b'TLB2':raise ValueError
    p=4;n,p=uv(rep,p);hl,p=uv(rep,p);headers=rep[p:p+hl];p+=hl; desc=[]
    for i in range(n):
        g=rep[p];p+=1;sz,p=uv(rep,p);pl,p=uv(rep,p);flag=rep[p:p+1];p+=1; pad=None
        if flag==b'1':q,p=uv(rep,p);pad=rep[p:p+q];p+=q
        desc.append((g,sz,pl,pad))
    ll,p=uv(rep,p); text=lex_unpack(rep[p:p+ll]);p+=ll; bl,p=uv(rep,p);binary=rep[p:p+bl];p+=bl;tl,p=uv(rep,p);tail=rep[p:p+tl];p+=tl
    if p!=len(rep):raise ValueError('trailing')
    tp=bp=0;o=bytearray()
    for i,(g,sz,pl,pad) in enumerate(desc):
        o+=headers[i*512:(i+1)*512]
        if g==0:o+=text[tp:tp+sz];tp+=sz
        else:o+=binary[bp:bp+sz];bp+=sz
        o+=pad if pad is not None else b'\0'*pl
    o+=tail
    if tp!=len(text) or bp!=len(binary):raise ValueError('bands')
    return bytes(o)

def signed_res(cur,pred):
    r=((cur.astype(np.int16)-pred.astype(np.int16)+128)&255)-128
    return np.where(r>=0,2*r,-2*r-1).astype(np.uint8)
def unzig(z):
    z=z.astype(np.int16);return np.where((z&1)==0,z//2,-((z+1)//2)).astype(np.int16)

def med_pred(a,b,c):
    lo=np.minimum(a,b); hi=np.maximum(a,b)
    return np.where(c>=hi,lo,np.where(c<=lo,hi,a.astype(np.int16)+b.astype(np.int16)-c.astype(np.int16))).astype(np.uint8)

def shift_prev(prev,dx,dy):
    h,w=prev.shape;o=np.empty_like(prev)
    xs=np.clip(np.arange(w)-dx,0,w-1);ys=np.clip(np.arange(h)-dy,0,h-1)
    o[:]=prev[np.ix_(ys,xs)];return o

def global_shift(prev,cur,rad=8):
    a=prev[::4,::4].astype(np.int16); b=cur[::4,::4].astype(np.int16); best=(10**18,0,0)
    for dy in range(-rad,rad+1):
      for dx in range(-rad,rad+1):
        sy=dy//4;sx=dx//4; y0=max(0,sy);y1=min(a.shape[0],a.shape[0]+sy);x0=max(0,sx);x1=min(a.shape[1],a.shape[1]+sx)
        yy=max(0,-sy);xx=max(0,-sx);hh=y1-y0;ww=x1-x0
        if hh<8 or ww<8:continue
        sc=np.abs(b[y0:y1,x0:x1]-a[yy:yy+hh,xx:xx+ww]).sum()
        if sc<best[0]:best=(int(sc),dx,dy)
    return best[1],best[2]

def pred_plane(frames,block=16,motion=True):
    nf,h,w=frames.shape;res=np.empty_like(frames); ids=[]; shifts=[]
    for t in range(nf):
        fr=frames[t];prev=frames[t-1] if t else None;dx=dy=0
        if t and motion: dx,dy=global_shift(prev,fr,8)
        shifts.append((dx,dy));mprev=shift_prev(prev,dx,dy) if t else None
        for y0 in range(0,h,block):
          y1=min(h,y0+block)
          for x0 in range(0,w,block):
            x1=min(w,x0+block);yy,xx=np.mgrid[y0:y1,x0:x1]
            left=np.where(xx>0,fr[yy,np.maximum(xx-1,0)],0).astype(np.uint8)
            up=np.where(yy>0,fr[np.maximum(yy-1,0),xx],left).astype(np.uint8)
            ul=np.where((xx>0)&(yy>0),fr[np.maximum(yy-1,0),np.maximum(xx-1,0)],up).astype(np.uint8)
            preds=[med_pred(left,up,ul),left,up]
            if t:
              tp=mprev[yy,xx];tpl=np.where(xx>0,mprev[yy,np.maximum(xx-1,0)],tp);tpu=np.where(yy>0,mprev[np.maximum(yy-1,0),xx],tp)
              preds += [tp,((tp.astype(np.int16)+left.astype(np.int16)-tpl.astype(np.int16))&255).astype(np.uint8),((tp.astype(np.int16)+up.astype(np.int16)-tpu.astype(np.int16))&255).astype(np.uint8)]
            cur=fr[yy,xx];scores=[]
            for pr in preds:
                r=((cur.astype(np.int16)-pr.astype(np.int16)+128)&255)-128;scores.append(int(np.abs(r).sum()))
            k=int(np.argmin(scores));ids.append(k);res[t,y0:y1,x0:x1]=signed_res(cur,preds[k])
    return res.tobytes(), bytes(ids), bytes((dx+16)&31 for dx,dy in shifts)+bytes((dy+16)&31 for dx,dy in shifts)

def video_pack(raw,w=320,h=180):
    fs=w*h*3//2
    if len(raw)%fs:return None
    nf=len(raw)//fs; a=np.frombuffer(raw,dtype=np.uint8);Y=[];U=[];V=[];p=0
    for _ in range(nf):
        Y.append(a[p:p+w*h].reshape(h,w));p+=w*h;U.append(a[p:p+w*h//4].reshape(h//2,w//2));p+=w*h//4;V.append(a[p:p+w*h//4].reshape(h//2,w//2));p+=w*h//4
    bands=[]
    for arr in (np.stack(Y),np.stack(U),np.stack(V)): bands.append(pred_plane(arr,16 if arr.shape[2]>=300 else 8,True))
    o=bytearray(b'VLB2')+struct.pack('<HHI',w,h,nf)
    for r,i,s in bands:o+=vi(len(r))+r+vi(len(i))+i+vi(len(s))+s
    return bytes(o)

def video_unpack(rep):
    if rep[:4]!=b'VLB2':raise ValueError
    p=4;w,h,nf=struct.unpack_from('<HHI',rep,p);p+=8;outs=[]
    for ph,pw,block in ((h,w,16),(h//2,w//2,8),(h//2,w//2,8)):
      rl,p=uv(rep,p);rz=np.frombuffer(rep[p:p+rl],dtype=np.uint8).reshape(nf,ph,pw);p+=rl;il,p=uv(rep,p);ids=rep[p:p+il];p+=il;sl,p=uv(rep,p);s=rep[p:p+sl];p+=sl
      dxs=[(x&31)-16 for x in s[:nf]];dys=[(x&31)-16 for x in s[nf:2*nf]];frs=np.empty((nf,ph,pw),dtype=np.uint8);ip=0
      for t in range(nf):
        fr=np.zeros((ph,pw),dtype=np.uint8);prev=frs[t-1] if t else None;mp=shift_prev(prev,dxs[t],dys[t]) if t else None
        for y0 in range(0,ph,block):
          y1=min(ph,y0+block)
          for x0 in range(0,pw,block):
            x1=min(pw,x0+block);yy,xx=np.mgrid[y0:y1,x0:x1]
            left=np.where(xx>0,fr[yy,np.maximum(xx-1,0)],0).astype(np.uint8);up=np.where(yy>0,fr[np.maximum(yy-1,0),xx],left).astype(np.uint8);ul=np.where((xx>0)&(yy>0),fr[np.maximum(yy-1,0),np.maximum(xx-1,0)],up).astype(np.uint8)
            preds=[med_pred(left,up,ul),left,up]
            if t:
              tp=mp[yy,xx];tpl=np.where(xx>0,mp[yy,np.maximum(xx-1,0)],tp);tpu=np.where(yy>0,mp[np.maximum(yy-1,0),xx],tp);preds += [tp,((tp.astype(np.int16)+left.astype(np.int16)-tpl.astype(np.int16))&255).astype(np.uint8),((tp.astype(np.int16)+up.astype(np.int16)-tpu.astype(np.int16))&255).astype(np.uint8)]
            k=ids[ip];ip+=1;rr=unzig(rz[t,y0:y1,x0:x1]);fr[y0:y1,x0:x1]=((preds[k].astype(np.int16)+rr)&255).astype(np.uint8)
        frs[t]=fr
      outs.append(frs)
    if p!=len(rep):raise ValueError('video trailing')
    o=bytearray()
    for t in range(nf):o+=outs[0][t].tobytes()+outs[1][t].tobytes()+outs[2][t].tobytes()
    return bytes(o)

def prepare():
    sh(f"rm -rf '{D}/android-src' '{D}/zlib-src'; mkdir -p '{D}'")
    sh(f"git clone -q --depth 1 https://github.com/android/architecture-samples.git '{D}/android-src'; rm -rf '{D}/android-src/.git'; tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{D}/android.tar' -C '{D}/android-src' app build.gradle.kts settings.gradle.kts gradle.properties 2>/dev/null || tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{D}/android.tar' -C '{D}/android-src' app")
    sh(f"git clone -q --depth 1 https://github.com/madler/zlib.git '{D}/zlib-src'; rm -rf '{D}/zlib-src/.git'; tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{D}/source.tar' -C '{D}/zlib-src' .")
    sh(f"curl -L --retry 3 -sS https://media.w3.org/2010/05/sintel/trailer.mp4 -o '{D}/video.mp4'; ffmpeg -loglevel error -y -ss 0 -t 4 -i '{D}/video.mp4' -vf scale=320:180 -r 24 -f rawvideo -pix_fmt yuv420p '{D}/video.raw'")

def main():
    prepare();rows=[]
    for name,path,pack,unpack in [('android_app',f'{D}/android.tar',tar_pack,tar_unpack),('source_tree',f'{D}/source.tar',tar_pack,tar_unpack),('raw_video',f'{D}/video.raw',video_pack,video_unpack)]:
      raw=open(path,'rb').read();print('PACK',name,len(raw),flush=True);rep=pack(raw);print('REP',len(rep),flush=True);dec=unpack(rep);exact=(dec==raw);print('EXACT',exact,flush=True)
      if not exact:raise SystemExit(name+' roundtrip failed')
      r=outer_sizes(name,raw,rep);r.update(category=name,original=len(raw),rep=len(rep),exact=exact);rows.append(r);print('RESULT',json.dumps(r),flush=True)
    open(os.path.join(O,'beast_results.json'),'w').write(json.dumps(rows,indent=2))
if __name__=='__main__':main()
