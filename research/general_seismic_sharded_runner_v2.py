"""Scalable execution hook for general_seismic_sharded_runner.

For SEG-Y, source records are shared read-only across execution shards while
fixed-layout channel groups are partitioned exactly by group_index % shard_count.
All other formats retain the frozen complete-record sharding of v1.
"""
import copy

import general_seismic_sharded_runner as old

_orig_shard_row = old.shard_row
_orig_iter_panels = old.base.iter_panels


def shard_row(row, ds, shard_index, shard_count):
    if ds.get('format') == 'SEG-Y':
        shard_index=int(shard_index);shard_count=int(shard_count)
        if shard_count<=0 or not (0<=shard_index<shard_count):raise ValueError((shard_index,shard_count))
        q=copy.deepcopy(row)
        # Every SEG-Y execution worker sees the same immutable frozen logical
        # source objects; the streaming reader seeks only to its trace groups.
        q['execution_panel_shard']={'index':shard_index,'count':shard_count,'unit':'channel_group_modulo'}
        # Source-byte accounting is survey metadata, not work performed. Charge
        # it exactly once when shard results are collapsed.
        original_bytes=int(row.get('selected_bytes',0))
        q['selected_bytes']=original_bytes if shard_index==0 else 0
        q['selected_gb']=q['selected_bytes']/1e9
        q['execution_shard']={'index':shard_index,'count':shard_count,'record_count':len(old.base.records(row)),'source_records_shared_read_only':True}
        return q
    return _orig_shard_row(row,ds,shard_index,shard_count)


def iter_panels(ds,row,cfg,tmp,cube2mseed=None):
    if ds.get('format')!='SEG-Y':
        yield from _orig_iter_panels(ds,row,cfg,tmp,cube2mseed);return
    from general_seismic_streaming_segy import s3_panels
    channels,time_samples=old.base.panel_dims(cfg)
    sh=row.get('execution_panel_shard')
    kw={'channels':channels,'time_samples':time_samples}
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


# Patch module globals used dynamically by the already-audited v1 execution
# functions; codec/statistical code itself is unchanged.
old.shard_row=shard_row
old.base.iter_panels=iter_panels


if __name__=='__main__':
    old.main()
