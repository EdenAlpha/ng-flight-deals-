"""Minimal strict SEG-D rev2.x demultiplexed waveform reader.

Implements only the standard demultiplexed sample formats needed by the frozen
Crescent Valley benchmark. Header interpretation follows SEG-D rev2.1 and the
older MIT drsudow/SEG-D reader, but trace decoding is pure numpy and validates
all byte boundaries before yielding data.
"""
from dataclasses import dataclass
from typing import List
import os
import numpy as np


def pbcd(bs):
    v=0
    for b in bs:
        hi=(int(b)>>4)&15;lo=int(b)&15
        if hi>9 or lo>9: raise ValueError(('invalid packed BCD',bytes(bs).hex()))
        v=v*100+hi*10+lo
    return v

@dataclass
class ChannelSet:
    number:int
    start_ms:int
    stop_ms:int
    channels:int
    trace_header_bytes:int=0
    samples:int=0
    entry:int=0
    trace_bytes:int=0

class SegdRev2:
    def __init__(self,path):
        self.path=path;self.file_size=os.path.getsize(path);self.channel_sets=[]
        with open(path,'rb') as f:self._parse(f)

    def _parse(self,f):
        g1=f.read(32);g2=f.read(32);g3=f.read(32)
        if len(g3)!=32:raise RuntimeError('truncated general header')
        self.file_number=pbcd(g1[0:2]);self.format_code=pbcd(g1[2:4])
        self.revision=pbcd(g2[10:11])+pbcd(g2[11:12])/10.0
        if not (1.0 <= self.revision < 3.0):raise RuntimeError(('not SEG-D rev1/2',self.revision))
        # Rev2.1 General Header #1 byte 23 high nibble = base scan interval in 2 ms units.
        # The historical reader expresses this as seconds; keep exact seconds here.
        self.dt_seconds=((g1[22]>>4)&15)*1e-3
        if self.dt_seconds<=0:raise RuntimeError(('invalid base scan interval',g1[22]))
        self.n_scan_types=pbcd(g1[27:28])
        self.n_channel_sets=pbcd(g1[28:29])
        self.skew_blocks=pbcd(g1[29:30])
        self.extended_blocks=pbcd(g1[30:31]);self.external_blocks=pbcd(g1[31:32])
        if self.extended_blocks==165:self.extended_blocks=int.from_bytes(g2[5:7],'big')
        if self.external_blocks==165:self.external_blocks=int.from_bytes(g2[7:9],'big')
        if self.n_scan_types not in (0,1):raise RuntimeError(('unsupported scan type count',self.n_scan_types))
        if self.n_channel_sets<=0 or self.n_channel_sets>255:raise RuntimeError(('bad channel set count',self.n_channel_sets))
        # Rev<3 channel set descriptor is one 32-byte block per channel set.
        for _ in range(self.n_channel_sets):
            h=f.read(32)
            if len(h)!=32:raise RuntimeError('truncated channel-set descriptor')
            number=pbcd(h[1:2]);start=(h[2]*256+h[3])*2;stop=(h[4]*256+h[5])*2;channels=pbcd(h[8:10])
            if channels<=0:raise RuntimeError(('bad channel count',number,channels))
            self.channel_sets.append(ChannelSet(number,start,stop,channels))
        # Rev2 skew blocks follow channel-set descriptors.
        if self.skew_blocks:f.seek(32*self.skew_blocks,1)
        # The frozen Crescent files are Fairfield/nodal rev2 and contain extended/external
        # headers whose lengths are declared in GH1/GH2. Skip exactly those declared blocks.
        if self.extended_blocks:f.seek(32*self.extended_blocks,1)
        if self.external_blocks:f.seek(32*self.external_blocks,1)
        self.trace_area_start=f.tell()
        self._index_traces(f)

    def _bytes_per_sample(self):
        return {8036:3,8038:4,8058:4,8080:8}.get(self.format_code)

    def _dtype(self):
        return {8038:np.dtype('>i4'),8058:np.dtype('>f4'),8080:np.dtype('>f8')}.get(self.format_code)

    def _index_traces(self,f):
        bps=self._bytes_per_sample()
        if bps is None:raise RuntimeError(('unsupported SEG-D format code',self.format_code))
        pos=self.trace_area_start
        for ci,cs in enumerate(self.channel_sets):
            f.seek(pos);th=f.read(20)
            if len(th)!=20:raise RuntimeError(('missing first trace header',ci,pos,self.file_size))
            ext=int(th[9]);hdr=20+32*ext
            # Standard rev2 channel-set start/end are in ms; dt_seconds is seconds/sample.
            samples=int(round((cs.stop_ms-cs.start_ms)/(self.dt_seconds*1000.0)))
            if samples<=0:raise RuntimeError(('bad sample count',ci,cs.start_ms,cs.stop_ms,self.dt_seconds))
            tbytes=hdr+samples*bps
            end=pos+cs.channels*tbytes
            if end>self.file_size:raise RuntimeError(('trace area overruns file',ci,pos,end,self.file_size,cs.channels,hdr,samples,bps))
            cs.trace_header_bytes=hdr;cs.samples=samples;cs.entry=pos;cs.trace_bytes=tbytes
            pos=end
        self.trace_area_end=pos
        # Trailers/vendor padding may remain, but trace payload can never exceed file size.
        if self.trace_area_end>self.file_size:raise RuntimeError('indexed past EOF')

    def _read24(self,b,n):
        a=np.frombuffer(b,np.uint8)
        if a.size!=3*n:raise RuntimeError(('short 24-bit trace',a.size,n))
        a=a.reshape(n,3).astype(np.int32);v=(a[:,0]<<16)|(a[:,1]<<8)|a[:,2]
        neg=(v & 0x800000)!=0;v[neg]-=1<<24
        return v

    def read_channel_set(self,index,time_limit=None):
        cs=self.channel_sets[int(index)];n=cs.samples if time_limit is None else min(cs.samples,int(time_limit));bps=self._bytes_per_sample();out=np.empty((cs.channels,n),np.float64 if self.format_code==8080 else np.float32)
        with open(self.path,'rb') as f:
            for tr in range(cs.channels):
                base=cs.entry+tr*cs.trace_bytes;f.seek(base+cs.trace_header_bytes);raw=f.read(cs.samples*bps)
                if len(raw)!=cs.samples*bps:raise RuntimeError(('short trace data',index,tr,len(raw),cs.samples*bps))
                if self.format_code==8036:a=self._read24(raw,cs.samples).astype(np.float32)
                else:a=np.frombuffer(raw,dtype=self._dtype(),count=cs.samples).astype(out.dtype,copy=False)
                out[tr]=a[:n]
        if not np.all(np.isfinite(out)):raise RuntimeError(('nonfinite decoded SEG-D samples',index))
        return out

    def summary(self):
        return {'file_size':self.file_size,'file_number':self.file_number,'format_code':self.format_code,'revision':self.revision,'dt_seconds':self.dt_seconds,'n_scan_types':self.n_scan_types,'n_channel_sets':self.n_channel_sets,'extended_blocks':self.extended_blocks,'external_blocks':self.external_blocks,'trace_area_start':self.trace_area_start,'trace_area_end':self.trace_area_end,'trailing_bytes':self.file_size-self.trace_area_end,'channel_sets':[vars(x) for x in self.channel_sets]}

def segd_rev2_panels(path,channels=128,time_limit=None,max_panels=None):
    s=SegdRev2(path);nout=0
    for csi,cs in enumerate(s.channel_sets):
        A=s.read_channel_set(csi,time_limit)
        for c0 in range(0,A.shape[0],int(channels)):
            P=np.ascontiguousarray(A[c0:min(c0+int(channels),A.shape[0])])
            if P.size:
                yield P,{'format':'SEG-D','revision':s.revision,'format_code':s.format_code,'channel_set_index':csi,'channel0':c0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':s.format_code in (8036,8038),'source_dtype':str(P.dtype)}
                nout+=1
                if max_panels is not None and nout>=int(max_panels):return
