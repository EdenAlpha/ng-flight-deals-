"""Sequential SEG-Y numeric reader with local/S3/multipart support.

Designed for the frozen general seismic benchmark: headers are parsed only to
recover numeric trace samples. The same numeric values are supplied to our codec
and SZ3. No geometry or acquisition metadata is used for routing.
"""
import io, os, struct
import numpy as np

TEXT=3200; BINARY=400; TRACE_HEADER=240

class LocalSequential:
    def __init__(self,path):self.f=open(path,'rb');self.size=os.path.getsize(path);self.pos=0
    def read(self,n=-1):
        b=self.f.read(n);self.pos+=len(b);return b
    def tell(self):return self.pos
    def close(self):self.f.close()

class S3ConcatSequential:
    def __init__(self,client,objects,block_bytes=16*1024*1024):
        self.s3=client;self.objects=list(objects);self.block=int(block_bytes);self.i=0;self.opos=0;self.pos=0;self.cache=b'';self.cache_start=-1
        self.sizes=[int(o['size']) for o in self.objects];self.size=sum(self.sizes)
    def _fill(self):
        while self.i<len(self.objects) and self.opos>=self.sizes[self.i]:self.i+=1;self.opos=0;self.cache=b'';self.cache_start=-1
        if self.i>=len(self.objects):return False
        o=self.objects[self.i];start=self.opos;end=min(self.sizes[self.i]-1,start+self.block-1)
        self.cache=self.s3.get_object(Bucket=o['bucket'],Key=o['key'],Range=f'bytes={start}-{end}')['Body'].read();self.cache_start=start
        if not self.cache:raise RuntimeError(('empty S3 range',o,start,end))
        return True
    def read(self,n=-1):
        if n is None or n<0:n=self.size-self.pos
        n=min(int(n),self.size-self.pos);out=[];need=n
        while need>0:
            if self.i>=len(self.objects):break
            if not (self.cache_start<=self.opos<self.cache_start+len(self.cache)):
                if not self._fill():break
            off=self.opos-self.cache_start;take=min(need,len(self.cache)-off,self.sizes[self.i]-self.opos)
            if take<=0:
                self.i+=1;self.opos=0;self.cache=b'';self.cache_start=-1;continue
            out.append(self.cache[off:off+take]);self.opos+=take;self.pos+=take;need-=take
            if self.opos>=self.sizes[self.i]:self.i+=1;self.opos=0;self.cache=b'';self.cache_start=-1
        b=b''.join(out)
        if len(b)!=n:raise EOFError(('short concatenated read',len(b),n,self.pos,self.size))
        return b
    def tell(self):return self.pos
    def close(self):pass

def _u16(b,endian='>'):return struct.unpack(endian+'H',b)[0]
def _i16(b,endian='>'):return struct.unpack(endian+'h',b)[0]

def ibm32_to_float(raw,endian='>'):
    u=np.frombuffer(raw,dtype=np.dtype(endian+'u4')).astype(np.uint32,copy=False)
    sign=np.where((u>>31)!=0,-1.0,1.0);exp=((u>>24)&0x7f).astype(np.int32)-64;frac=(u&0x00ffffff).astype(np.float64)/float(1<<24)
    y=sign*frac*np.power(16.0,exp);y[u==0]=0.0
    return y.astype(np.float32)

def int24_to_float(raw,endian='>'):
    a=np.frombuffer(raw,np.uint8)
    if a.size%3:raise RuntimeError('bad int24 byte count')
    a=a.reshape(-1,3).astype(np.int32)
    if endian=='>':v=(a[:,0]<<16)|(a[:,1]<<8)|a[:,2]
    else:v=(a[:,2]<<16)|(a[:,1]<<8)|a[:,0]
    neg=(v&0x800000)!=0;v[neg]-=1<<24
    return v.astype(np.float32)

def sample_info(code,endian):
    code=int(code)
    return {
      1:(4,None),2:(4,np.dtype(endian+'i4')),3:(2,np.dtype(endian+'i2')),5:(4,np.dtype(endian+'f4')),
      6:(8,np.dtype(endian+'f8')),7:(3,None),8:(1,np.dtype('i1')),9:(8,np.dtype(endian+'i8')),
      10:(4,np.dtype(endian+'u4')),11:(2,np.dtype(endian+'u2')),12:(8,np.dtype(endian+'u8')),16:(1,np.dtype('u1'))
    }.get(code,(None,None))

def decode_samples(raw,code,endian='>'):
    bps,dt=sample_info(code,endian)
    if bps is None:raise RuntimeError(('unsupported SEG-Y sample format',code))
    if len(raw)%bps:raise RuntimeError(('sample byte count not divisible',len(raw),bps))
    if code==1:return ibm32_to_float(raw,endian)
    if code==7:return int24_to_float(raw,endian)
    return np.frombuffer(raw,dtype=dt).astype(np.float32,copy=False)

class SegySequential:
    def __init__(self,reader):
        self.r=reader;self.text=reader.read(TEXT);bh=reader.read(BINARY)
        if len(self.text)!=TEXT or len(bh)!=BINARY:raise RuntimeError('truncated SEG-Y headers')
        # SEG-Y rev0/1 is normally big-endian. Detect little-endian only when big
        # interpretation gives an impossible sample format/count and little is sane.
        def fields(e):return _u16(bh[20:22],e),_u16(bh[24:26],e),_i16(bh[304:306],e),_i16(bh[350:352],e)
        big=fields('>');little=fields('<')
        known={1,2,3,5,6,7,8,9,10,11,12,16}
        def sane(q):return 0<q[0]<=65535 and q[1] in known
        if sane(big):self.endian='>';ns,fmt,rev,ext=big
        elif sane(little):self.endian='<';ns,fmt,rev,ext=little
        else:raise RuntimeError(('cannot determine SEG-Y endian/format',big,little))
        self.binary=bh;self.binary_ns=int(ns);self.format_code=int(fmt);self.revision_raw=int(rev);self.ext_text_count=max(0,int(ext))
        # Fixed-count extended textual headers. The rare -1 stanza terminator mode is
        # deliberately rejected rather than guessed.
        if ext==-1:raise RuntimeError('SEG-Y variable extended textual headers (-1) unsupported')
        if self.ext_text_count:reader.read(TEXT*self.ext_text_count)
        self.trace_start=reader.tell();self.trace_index=0
    def next_trace(self):
        th=self.r.read(TRACE_HEADER) if self.r.tell()<self.r.size else b''
        if not th:return None
        if len(th)!=TRACE_HEADER:raise RuntimeError(('truncated SEG-Y trace header',self.trace_index,len(th)))
        ns=_u16(th[114:116],self.endian) or self.binary_ns
        bps,_=sample_info(self.format_code,self.endian)
        if bps is None:raise RuntimeError(('unsupported sample format',self.format_code))
        raw=self.r.read(int(ns)*int(bps));a=decode_samples(raw,self.format_code,self.endian)
        if a.size!=ns:raise RuntimeError(('decoded sample mismatch',a.size,ns))
        self.trace_index+=1
        return a,th
    def panels(self,channels=128,max_panels=None,time_limit=None):
        rows=[];nout=0
        while True:
            q=self.next_trace()
            if q is None:
                if rows:
                    lens={len(a) for a,_ in rows}
                    if len(lens)!=1:raise RuntimeError(('variable trace lengths within panel',lens))
                    P=np.stack([a for a,_ in rows]);
                    if time_limit is not None:P=P[:,:int(time_limit)]
                    yield np.ascontiguousarray(P),self._meta(P)
                break
            rows.append(q)
            if len(rows)>=int(channels):
                lens={len(a) for a,_ in rows}
                if len(lens)!=1:raise RuntimeError(('variable trace lengths within panel',lens))
                P=np.stack([a for a,_ in rows]);
                if time_limit is not None:P=P[:,:int(time_limit)]
                yield np.ascontiguousarray(P),self._meta(P);nout+=1;rows=[]
                if max_panels is not None and nout>=int(max_panels):return
    def _meta(self,P):
        return {'format':'SEG-Y','format_code':self.format_code,'endian':self.endian,'binary_ns':self.binary_ns,'revision_raw':self.revision_raw,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':self.format_code in (2,3,7,8,9,10,11,12,16),'source_dtype':'decoded_float32','logical_size':int(self.r.size)}

def local_panels(path,**kw):
    r=LocalSequential(path)
    try:yield from SegySequential(r).panels(**kw)
    finally:r.close()

def s3_panels(client,objects,**kw):
    r=S3ConcatSequential(client,objects)
    try:yield from SegySequential(r).panels(**kw)
    finally:r.close()
