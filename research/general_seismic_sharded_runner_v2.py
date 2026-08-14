"""Scalable execution hook for the frozen general-seismic benchmark.

Low-file/assembled SEG-Y volumes are partitioned by fixed-layout channel groups.
SEG-Y surveys with enough independent files retain complete-record sharding.
All other formats retain complete-record sharding.  San Emidio DATA-CUBE files
are decoded by the official GFZ cube2mseed utility to INT32 counts without an
explicit waveform resampling request.
"""
import copy
import general_seismic_sharded_runner as old

_orig_shard_row=old.shard_row
_orig_iter_panels=old.base.iter_panels


def _panel_shard_needed(row,ds,shard_count):
    return ds.get('format')=='SEG-Y' and (bool(ds.get('assembly')) or len(old.base.records(row))<int(shard_count))


def shard_row(row,ds,shard_index,shard_count):
    shard_index=int(shard_index);shard_count=int(shard_count)
    if _panel_shard_needed(row,ds,shard_count):
        if shard_count<=0 or not (0<=shard_index<shard_count):raise ValueError((shard_index,shard_count))
        q=copy.deepcopy(row)
        q['execution_panel_shard']={'index':shard_index,'count':shard_count,'unit':'channel_group_modulo'}
        original_bytes=int(row.get('selected_bytes',0))
        q['selected_bytes']=original_bytes if shard_index==0 else 0
        q['selected_gb']=q['selected_bytes']/1e9
        q['execution_shard']={'index':shard_index,'count':shard_count,'record_count':len(old.base.records(row)),'source_records_shared_read_only':True,'mode':'segy_channel_groups'}
        return q
    q=_orig_shard_row(row,ds,shard_index,shard_count)
    q.setdefault('execution_shard',{})['mode']='complete_records'
    return q


def iter_panels(ds,row,cfg,tmp,cube2mseed=None):
    if ds.get('format')!='SEG-Y':
        yield from _orig_iter_panels(ds,row,cfg,tmp,cube2mseed);return
    from general_seismic_streaming_segy import s3_panels
    channels,time_samples=old.base.panel_dims(cfg)
    sh=row.get('execution_panel_shard');kw={'channels':channels,'time_samples':time_samples}
    if sh:
        kw['group_shard_index']=int(sh['index']);kw['group_shard_count']=int(sh['count'])
    rr=old.base.records(row)
    if ds.get('assembly'):
        for P,m in s3_panels(old.base.S3,rr,**kw):
            m.update(dataset_id=ds['id'],logical_file='assembled:'+','.join(o['key'] for o in rr));yield P,m
        return
    for o in rr:
        for P,m in s3_panels(old.base.S3,[o],**kw):
            m.update(dataset_id=ds['id'],logical_file=o['key']);yield P,m


def au4_segments_raw_counts(path,cube2mseed,work):
    """Decode native DATA-CUBE AU4 to integer counts with no explicit resampling."""
    from obspy import read
    b=old.base
    outdir=b.os.path.join(work,'mseed');b.os.makedirs(outdir,exist_ok=True)
    b.subprocess.run([cube2mseed,f'--output-dir={outdir}','--encoding=INT-32',path],check=True,stdout=b.subprocess.DEVNULL,stderr=b.subprocess.STDOUT)
    traces=[]
    for f in sorted(b.glob.glob(outdir+'/**/*',recursive=True)):
        if not b.os.path.isfile(f):continue
        try:st=read(f)
        except Exception:continue
        traces.extend(st)
    if not traces:raise RuntimeError(('cube2mseed produced no readable traces',path))
    groups=b.defaultdict(list)
    for tr in traces:
        key=(round(float(tr.stats.starttime.timestamp),6),int(tr.stats.npts),round(float(tr.stats.sampling_rate),9));groups[key].append(tr)
    for key in sorted(groups):
        gg=sorted(groups[key],key=lambda tr:(str(tr.id),str(tr.stats.channel)));A=[]
        for tr in gg:
            a=b.np.asarray(tr.data)
            if not b.np.issubdtype(a.dtype,b.np.integer):raise RuntimeError(('AU4 conversion not integer counts',tr.id,a.dtype))
            A.append(a.astype(b.np.int32,copy=False))
        lens={a.size for a in A}
        if len(lens)!=1:raise RuntimeError(('AU4 aligned segment length mismatch',key,lens))
        yield b.np.ascontiguousarray(b.np.stack(A)),{'segment_start':key[0],'sampling_rate':key[2],'channel_ids':[str(tr.id) for tr in gg],'conversion':'GFZ cube2mseed INT-32; no explicit resampling'}

old.shard_row=shard_row
old.base.iter_panels=iter_panels
old.base.au4_segments=au4_segments_raw_counts

if __name__=='__main__':old.main()
