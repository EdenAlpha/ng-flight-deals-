"""Sequential SEG-Y numeric reader with local/S3/multipart support.

Headers are used only to recover numeric samples. The same numeric values are
fed to our portfolio and SZ3; geometry/labels never influence routing.
"""
import os, struct, bisect
import numpy as np

TEXT=3200; BINARY=400; TRACE_HEADER=240

class LocalSequential:
    def __init__(self,path):self.f=open(path,'rb');self.size=os.path.getsize(path);self.pos=0
    def read(self,n=-1):
        b=self.f.read(n);self.pos+=len(b);return b
    def tell(self):return self.pos
    def seek(self,pos):self.f.seek(int(pos));self.pos=int(pos);return self.pos
    def close(self):self.f.close()

class S3ConcatSequential:
    def __init__(self,client,objects,block_bytes=16*1024*1024):
        self.s3=client;self.objects=list(objects);self.block=int(block_bytes);self.sizes=[int(o['size']) for o in self.objects];self.ends=[];s=0
        for n in self.sizes:s+=n;self.ends.append(s)
        self.size=s;self.i=0;self.opos=0;self.pos=0;self.cache=b'';self.cache_start=-1
    def seek(self,pos):
        pos=int(pos)
        if pos<0 or pos>self.size:raise ValueError(('seek outside logical stream',pos,self.size))
        self.pos=pos;self.cache=b'';self.cache_start=-1
        if pos==self.size:self.i=len(self.objects);self.opos=0;return pos
        self.i=bisect.bisect_right(self.ends,pos);prev=0 if self.i==0 else self.ends[self.i-1];self.opos=pos-prev;return pos
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

def _u16(b,e='>'):return struct.unpack(e+'H',b)[0]
def _i16(b,e='>'):return struct.unpack(e+'h',b)[0]

def _flush_subnormal32(y):
    y=np.asarray(y,dtype=np.float32)
    tiny=np.float32(np.finfo(np.float32).tiny)
    mask=(np.abs(y)<tiny) & (y!=0)
    if np.any(mask):
        y=y.copy();y[mask]=np.float32(0.0)
    return y

def ibm32_to_float(raw,endian='>'):
    if endian=='>':
        try:
            import segyio
            words=np.frombuffer(raw,dtype=np.uint32)
            return _flush_subnormal32(segyio.tools.native(words,format=1,copy=True))
        except Exception:
            pass
    u=np.frombuffer(raw,dtype=np.dtype(endian+'u4')).astype(np.uint32,copy=False)
    sign=np.where((u>>31)!=0,-1.0,1.0);exp=((u>>24)&0x7f).astype(np.int32)-64;frac=(u&0x00ffffff).astype(np.float64)/float(1<<24)
    y=sign*frac*np.power(16.0,exp);y[u==0]=0.0
    return _flush_subnormal32(y.astype(np.float32))

def int24_to_float(raw,endian='>'):
    a=np.frombuffer(raw,np.uint8)
    if a.size%3:raise RuntimeError('bad int24 byte count')
    a=a.reshape(-1,3).astype(np.int32)
    v=(a[:,0]<<16)|(a[:,1]<<8)|a[:,2] if endian=='>' else (a[:,2]<<16)|(a[:,1]<<8)|a[:,0]
    neg=(v&0x800000)!=0;v[neg]-=1<<24
    return v.astype(np.float32)

def sample_info(code,endian):
    return {1:(4,None),2:(4,np.dtype(endian+'i4')),3:(2,np.dtype(endian+'i2')),5:(4,np.dtype(endian+'f4')),6:(8,np.dtype(endian+'f8')),7:(3,None),8:(1,np.dtype('i1')),9:(8,np.dtype(endian+'i8')),10:(4,np.dtype(endian+'u4')),11:(2,np.dtype(endian+'u2')),12:(8,np.dtype(endian+'u8')),16:(1,np.dtype('u1'))}.get(int(code),(None,None))

def decode_samples(raw,code,endian='>'):
    bps,dt=sample_info(code,endian)
    if bps is None:raise RuntimeError(('unsupported SEG-Y sample format',code))
    if len(raw)%bps:raise RuntimeError(('sample byte count not divisible',len(raw),bps))
    if int(code)==1:return ibm32_to_float(raw,endian)
    if int(code)==7:return int24_to_float(raw,endian)
    return np.frombuffer(raw,dtype=dt).astype(np.float32,copy=False)

class SegySequential:
    def __init__(self,reader):
        self.r=reader;self.text=reader.read(TEXT);bh=reader.read(BINARY)
        if len(self.text)!=TEXT or len(bh)!=BINARY:raise RuntimeError('truncated SEG-Y headers')
        def fields(e):return _u16(bh[20:22],e),_u16(bh[24:26],e),_u16(bh[300:302],e),_u16(bh[302:304],e),_i16(bh[304:306],e)
        big=fields('>');little=fields('<');known={1,2,3,5,6,7,8,9,10,11,12,16}
        sane=lambda q:0<q[0]<=65535 and q[1] in known and -1<=q[4]<10000
        if sane(big):self.endian='>';ns,fmt,rev,fixed,ext=big
        elif sane(little):self.endian='<';ns,fmt,rev,fixed,ext=little
        else:raise RuntimeError(('cannot determine SEG-Y endian/format',big,little))
        if ext==-1:raise RuntimeError('SEG-Y variable extended textual headers (-1) unsupported')
        self.binary=bh;self.binary_ns=int(ns);self.format_code=int(fmt);self.revision_raw=int(rev);self.fixed_length_flag=int(fixed);self.ext_text_count=max(0,int(ext))
        if self.ext_text_count:reader.read(TEXT*self.ext_text_count)
        self.trace_start=reader.tell();self.trace_index=0
        bps,_=sample_info(self.format_code,self.endian)
        self.binary_stride=(TRACE_HEADER+self.binary_ns*int(bps)) if bps and self.binary_ns>0 else 0
        self.trace_area_bytes=int(self.r.size-self.trace_start)
        self.binary_stride_exact=bool(self.binary_stride>TRACE_HEADER and self.trace_area_bytes>=self.binary_stride and self.trace_area_bytes%self.binary_stride==0)
        self.ns_policy='binary_exact_file_stride' if self.binary_stride_exact else 'trace_header_with_binary_fallback'
        self.total_traces=(self.trace_area_bytes//self.binary_stride) if self.binary_stride_exact else None
        if self.fixed_length_flag==1 and not self.binary_stride_exact:
            raise RuntimeError(('SEG-Y fixed-length framing mismatch',self.r.size,self.trace_start,self.binary_ns,self.format_code,self.binary_stride,self.trace_area_bytes%self.binary_stride if self.binary_stride else None))
    def next_trace(self):
        if self.r.tell()>=self.r.size:return None
        th=self.r.read(TRACE_HEADER)
        if len(th)!=TRACE_HEADER:raise RuntimeError(('truncated SEG-Y trace header',self.trace_index,len(th)))
        trace_ns=_u16(th[114:116],self.endian)
        ns=self.binary_ns if self.binary_stride_exact else (trace_ns or self.binary_ns)
        bps,_=sample_info(self.format_code,self.endian)
        if bps is None:raise RuntimeError(('unsupported sample format',self.format_code))
        raw=self.r.read(int(ns)*int(bps));a=decode_samples(raw,self.format_code,self.endian)
        if a.size!=ns:raise RuntimeError(('decoded sample mismatch',a.size,ns))
        self.trace_index+=1;return a,th
    def _yield_rows(self,rows,time_samples,time_limit,group_index=None,group_shard_index=None,group_shard_count=None):
        lens={len(a) for a,_ in rows}
        if len(lens)!=1:raise RuntimeError(('variable trace lengths within channel group',lens))
        P=np.stack([a for a,_ in rows]);limit=P.shape[1] if time_limit is None else min(P.shape[1],int(time_limit));ts=limit if time_samples is None else int(time_samples)
        for t0 in range(0,limit,ts):
            Q=np.ascontiguousarray(P[:,t0:min(t0+ts,limit)])
            if Q.size:
                m=self._meta(Q,t0);m['channel_group_index']=None if group_index is None else int(group_index)
                if group_shard_count is not None:
                    m['execution_group_shard']={'index':int(group_shard_index),'count':int(group_shard_count)}
                yield Q,m
    def panels(self,channels=128,time_samples=8192,max_panels=None,time_limit=None,group_shard_index=None,group_shard_count=None):
        channels=int(channels);nout=0
        use_shard=group_shard_count is not None
        if use_shard:
            group_shard_count=int(group_shard_count);group_shard_index=int(group_shard_index)
            if group_shard_count<=0 or not (0<=group_shard_index<group_shard_count):raise ValueError(('bad SEG-Y group shard',group_shard_index,group_shard_count))

        # Fast exact-layout path: seek directly to selected channel groups, so
        # sharding a single huge SEG-Y volume does not reread/decode other shards.
        if use_shard and self.binary_stride_exact:
            ng=(int(self.total_traces)+channels-1)//channels
            for gi in range(group_shard_index,ng,group_shard_count):
                t0=gi*channels;nt=min(channels,int(self.total_traces)-t0)
                self.r.seek(self.trace_start+t0*self.binary_stride);self.trace_index=t0;rows=[]
                for _ in range(nt):
                    q=self.next_trace()
                    if q is None:raise RuntimeError(('unexpected EOF in fixed SEG-Y shard',gi,t0,nt))
                    rows.append(q)
                for P,m in self._yield_rows(rows,time_samples,time_limit,gi,group_shard_index,group_shard_count):
                    yield P,m;nout+=1
                    if max_panels is not None and nout>=int(max_panels):return
            return

        rows=[];gi=0
        while True:
            q=self.next_trace()
            if q is not None:rows.append(q)
            if q is None or len(rows)>=channels:
                if rows:
                    selected=(not use_shard) or (gi%group_shard_count==group_shard_index)
                    if selected:
                        for P,m in self._yield_rows(rows,time_samples,time_limit,gi,group_shard_index if use_shard else None,group_shard_count if use_shard else None):
                            yield P,m;nout+=1
                            if max_panels is not None and nout>=int(max_panels):return
                    rows=[];gi+=1
                if q is None:break
    def _meta(self,P,t0):
        return {'format':'SEG-Y','format_code':self.format_code,'endian':self.endian,'binary_ns':self.binary_ns,'revision_raw':self.revision_raw,'fixed_length_flag':self.fixed_length_flag,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'time0':int(t0),'source_integer':self.format_code in (2,3,7,8,9,10,11,12,16),'source_dtype':'decoded_float32','logical_size':int(self.r.size),'ns_policy':self.ns_policy,'binary_stride':int(self.binary_stride),'binary_stride_exact':bool(self.binary_stride_exact),'total_traces':None if self.total_traces is None else int(self.total_traces)}

def local_panels(path,**kw):
    r=LocalSequential(path)
    try:yield from SegySequential(r).panels(**kw)
    finally:r.close()

def s3_panels(client,objects,**kw):
    r=S3ConcatSequential(client,objects)
    try:yield from SegySequential(r).panels(**kw)
    finally:r.close()
