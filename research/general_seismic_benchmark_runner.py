import argparse, copy, glob, json, math, os, shutil, subprocess, tempfile, time
from collections import Counter, defaultdict

import boto3
import numpy as np
from botocore import UNSIGNED
from botocore.config import Config

S3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10}))


def load_json(p):
    with open(p) as f:return json.load(f)

def dump_json(x,p):
    with open(p,'w') as f:json.dump(x,f,indent=2,sort_keys=True)

def records(row):
    out=[];seen=set()
    for span in row.get('selected',[]):
        for o in span.get('objects',[]):
            key=(o.get('bucket'),o.get('key'),o.get('member'),o.get('member_offset'),int(o.get('size',0)))
            if key not in seen:seen.add(key);out.append(o)
    return out

def dataset_row(preflight,dataset_id):
    q=[r for r in preflight['datasets'] if r['id']==dataset_id]
    if len(q)!=1:raise RuntimeError(('preflight dataset lookup',dataset_id,len(q)))
    if q[0].get('status')!='ok':raise RuntimeError(('preflight dataset not ok',q[0]))
    return q[0]

def dataset_def(manifest,dataset_id):
    q=[d for d in manifest['datasets'] if d['id']==dataset_id]
    if len(q)!=1:raise RuntimeError(('manifest dataset lookup',dataset_id,len(q)))
    return q[0]

def panel_dims(cfg):
    p=cfg['panel_contract'];return int(p['channels_per_panel']),int(p['time_samples_per_panel'])

def h5_hint(dataset_id):
    return {
        'das_imperial_valley_2020':('Acoustic','time_channels'),
        'das_forge_neubrex_2024':('Acoustic','time_channels'),
        'das_egs_collab_exp2':('/data_product/data','time_channels'),
    }.get(dataset_id,(None,'auto'))

def iter_segy(ds,row,channels,time_samples):
    from general_seismic_streaming_segy import s3_panels
    rr=records(row)
    if ds.get('assembly'):
        # Waka is one SEG-Y logical volume split into public S3 parts.
        for P,m in s3_panels(S3,rr,channels=channels,time_samples=time_samples):
            m.update(dataset_id=ds['id'],logical_file='assembled:'+','.join(o['key'] for o in rr));yield P,m
        return
    for o in rr:
        for P,m in s3_panels(S3,[o],channels=channels,time_samples=time_samples):
            m.update(dataset_id=ds['id'],logical_file=o['key']);yield P,m

def iter_hdf5(ds,row,channels,time_samples):
    from general_seismic_numeric_io import hdf5_s3_panels
    dpath,orient=h5_hint(ds['id'])
    for o in records(row):
        for P,m in hdf5_s3_panels(o['bucket'],o['key'],channels=channels,time_samples=time_samples,dataset=dpath,orientation=orient):
            m.update(dataset_id=ds['id'],logical_file=o['key']);yield P,m

def download_object(o,path):
    S3.download_file(o['bucket'],o['key'],path)
    if os.path.getsize(path)!=int(o['size']):raise RuntimeError(('object size mismatch',o,path,os.path.getsize(path)))

def iter_segd(ds,row,channels,time_samples,tmp):
    from general_seismic_segd_rev2 import SegdRev2
    for oi,o in enumerate(records(row)):
        path=os.path.join(tmp,f'input_{oi}.sgd');download_object(o,path);s=SegdRev2(path)
        for csi,cs in enumerate(s.channel_sets):
            A=s.read_channel_set(csi)
            for c0 in range(0,A.shape[0],channels):
                for t0 in range(0,A.shape[1],time_samples):
                    P=np.ascontiguousarray(A[c0:min(c0+channels,A.shape[0]),t0:min(t0+time_samples,A.shape[1])])
                    if P.size:
                        yield P,{'format':'SEG-D','revision':s.revision,'format_code':s.format_code,'channel_set_index':csi,'channel0':c0,'time0':t0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':s.format_code in (8036,8038),'source_dtype':str(P.dtype),'dataset_id':ds['id'],'logical_file':o['key']}
        os.remove(path)

def extract_tar_member(o,path):
    off=int(o['member_offset']);n=int(o['size']);body=S3.get_object(Bucket=o['bucket'],Key=o['key'],Range=f'bytes={off}-{off+n-1}')['Body']
    with open(path,'wb') as f:
        left=n
        while left:
            b=body.read(min(left,8*1024*1024))
            if not b:raise EOFError(('short tar member range',o,left))
            f.write(b);left-=len(b)
    if os.path.getsize(path)!=n:raise RuntimeError(('member size mismatch',o,path))

def au4_segments(path,cube2mseed,work):
    from obspy import read
    outdir=os.path.join(work,'mseed');os.makedirs(outdir,exist_ok=True)
    subprocess.run([cube2mseed,'--fringe-samples=NOMINAL','--resample=SINC',f'--output-dir={outdir}','--encoding=INT-32',path],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    traces=[]
    for f in sorted(glob.glob(outdir+'/**/*',recursive=True)):
        if not os.path.isfile(f):continue
        try:st=read(f)
        except Exception:continue
        traces.extend(st)
    if not traces:raise RuntimeError(('cube2mseed produced no readable traces',path))
    groups=defaultdict(list)
    for tr in traces:
        key=(round(float(tr.stats.starttime.timestamp),6),int(tr.stats.npts),round(float(tr.stats.sampling_rate),9))
        groups[key].append(tr)
    for key in sorted(groups):
        gg=sorted(groups[key],key=lambda tr:(str(tr.id),str(tr.stats.channel)))
        A=[]
        for tr in gg:
            a=np.asarray(tr.data)
            if not np.issubdtype(a.dtype,np.integer):raise RuntimeError(('AU4 conversion not integer counts',tr.id,a.dtype))
            A.append(a.astype(np.int32,copy=False))
        lens={a.size for a in A}
        if len(lens)!=1:raise RuntimeError(('AU4 aligned segment length mismatch',key,lens))
        yield np.ascontiguousarray(np.stack(A)),{'segment_start':key[0],'sampling_rate':key[2],'channel_ids':[str(tr.id) for tr in gg]}

def iter_au4(ds,row,channels,time_samples,tmp,cube2mseed):
    if not cube2mseed or not os.path.isfile(cube2mseed):raise RuntimeError(('CUBE2MSEED unavailable',cube2mseed))
    for oi,o in enumerate(records(row)):
        work=os.path.join(tmp,f'au4_{oi}');os.makedirs(work,exist_ok=True);path=os.path.join(work,'input.AU4');extract_tar_member(o,path)
        for A,sm in au4_segments(path,cube2mseed,work):
            for c0 in range(0,A.shape[0],channels):
                for t0 in range(0,A.shape[1],time_samples):
                    P=np.ascontiguousarray(A[c0:min(c0+channels,A.shape[0]),t0:min(t0+time_samples,A.shape[1])])
                    if P.size:
                        m={'format':'DataCube-AU4','channel0':c0,'time0':t0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':True,'source_dtype':'int32','dataset_id':ds['id'],'logical_file':o.get('member',o['key'])};m.update(sm);yield P,m
        shutil.rmtree(work,ignore_errors=True)

def iter_panels(ds,row,cfg,tmp,cube2mseed=None):
    channels,time_samples=panel_dims(cfg);fmt=ds['format']
    if ds['id']=='land_san_emidio_2021':yield from iter_au4(ds,row,channels,time_samples,tmp,cube2mseed);return
    if fmt=='SEG-Y':yield from iter_segy(ds,row,channels,time_samples);return
    if fmt=='HDF5':yield from iter_hdf5(ds,row,channels,time_samples);return
    if fmt=='SEGD':yield from iter_segd(ds,row,channels,time_samples,tmp);return
    raise RuntimeError(('no primary reader',ds['id'],fmt))

class Moments:
    def __init__(self):self.n=0;self.mean=0.0;self.M2=0.0;self.numeric_bytes=0;self.panels=0
    def add(self,A):
        x=np.asarray(A);n=int(x.size)
        if n==0:return
        y=x.astype(np.float64,copy=False);mu=float(np.mean(y,dtype=np.float64));d=y-mu;m2=float(np.sum(d*d,dtype=np.float64));
        if self.n==0:self.n=n;self.mean=mu;self.M2=m2
        else:
            delta=mu-self.mean;tot=self.n+n;self.M2+=m2+delta*delta*self.n*n/tot;self.mean+=delta*n/tot;self.n=tot
        self.numeric_bytes+=int(x.nbytes);self.panels+=1
    def result(self):
        if self.n<=0:raise RuntimeError('no numeric samples')
        var=self.M2/self.n
        if var<0 and abs(var)<1e-12*max(1.0,self.mean*self.mean):var=0.0
        if var<=0:raise RuntimeError(('nonpositive survey variance',var,self.n,self.mean))
        return {'samples':int(self.n),'mean':float(self.mean),'M2':float(self.M2),'std':float(math.sqrt(var)),'numeric_bytes':int(self.numeric_bytes),'panels':int(self.panels)}

def stats_pass(ds,row,cfg,tmp,cube2mseed):
    q=Moments();t=time.perf_counter()
    for i,(P,m) in enumerate(iter_panels(ds,row,cfg,tmp,cube2mseed),1):
        q.add(P)
        if i%100==0:print('STATS_PROGRESS',ds['id'],i,q.n,flush=True)
    r=q.result();r['seconds']=time.perf_counter()-t;return r

def short_cfg(cfg,nt):
    if int(nt)>32:return cfg
    q=copy.deepcopy(cfg);q['candidates']=[c for c in q['candidates'] if c['engine']!='ar32_zsm'];return q

def compression_pass(ds,row,cfg,eps,tmp,cube2mseed):
    import general_seismic_codec_portfolio as g
    from general_seismic_fast_backend import install
    from general_seismic_portfolio_optimized import encode_portfolio
    from general_seismic_numeric_io import matched_sz3
    install(g)
    ours=sz3=samples=0;panels=0;max_ours=max_sz3=0.0;engine=Counter();cid=Counter();enc_seconds=sz_seconds=0.0;tall=time.perf_counter()
    for i,(P,m) in enumerate(iter_panels(ds,row,cfg,tmp,cube2mseed),1):
        pcfg=short_cfg(cfg,P.shape[1]);t=time.perf_counter();blob,meta=encode_portfolio(g,P,eps,pcfg,bool(m.get('source_integer',False)));enc_seconds+=time.perf_counter()-t
        t=time.perf_counter();sb,sme=matched_sz3(P,eps);sz_seconds+=time.perf_counter()-t
        ours+=len(blob);sz3+=int(sb);samples+=int(P.size);panels+=1;max_ours=max(max_ours,float(meta['maxerr']));max_sz3=max(max_sz3,float(sme));engine[meta['selected_engine']]+=1;cid[str(meta['selected_id'])]+=1
        if meta['maxerr']>eps or sme>eps*(1+3e-6):raise RuntimeError(('hard bound failure',ds['id'],i,meta['maxerr'],sme,eps))
        if i%50==0:print('COMPRESS_PROGRESS',ds['id'],i,samples,ours,sz3,flush=True)
    if samples<=0:raise RuntimeError('compression pass saw no samples')
    return {'samples':samples,'panels':panels,'ours_bytes':ours,'sz3_bytes':sz3,'ours_bps':8.0*ours/samples,'sz3_bps':8.0*sz3/samples,'gain_sz3_over_ours':sz3/ours,'reduction_percent_vs_sz3':100.0*(1.0-ours/sz3),'ours_maxerr':max_ours,'sz3_maxerr':max_sz3,'engine_panel_counts':dict(engine),'candidate_panel_counts':dict(cid),'ours_encode_seconds':enc_seconds,'sz3_roundtrip_seconds':sz_seconds,'compression_pass_seconds':time.perf_counter()-tall}

def run_survey(args):
    manifest=load_json(args.manifest);pre=load_json(args.preflight);cfg=load_json(args.config);ds=dataset_def(manifest,args.dataset);row=dataset_row(pre,args.dataset)
    with tempfile.TemporaryDirectory(prefix='general_seismic_') as tmp:
        st=stats_pass(ds,row,cfg,tmp,args.cube2mseed);eps=0.10*st['std'];print('SURVEY_EPSILON',ds['id'],st['std'],eps,flush=True);co=compression_pass(ds,row,cfg,eps,tmp,args.cube2mseed)
    if co['samples']!=st['samples']:raise RuntimeError(('two-pass sample count mismatch',st['samples'],co['samples']))
    out={'benchmark':'general-seismic-benchmark-v1','dataset_id':ds['id'],'name':ds['name'],'category':ds['category'],'format':ds['format'],'selected_source_bytes':int(row.get('selected_bytes',0)),'selected_source_gb':float(row.get('selected_gb',0.0)),'global_stats':st,'epsilon':eps};out.update(co);dump_json(out,args.out);print(json.dumps(out,indent=2));return out

def percentile(xs,q):return float(np.percentile(np.asarray(xs,float),q))
def aggregate(args):
    rows=[]
    for f in sorted(glob.glob(os.path.join(args.results,'*.json'))):
        try:x=load_json(f)
        except Exception:continue
        if isinstance(x,dict) and 'dataset_id' in x and 'gain_sz3_over_ours' in x:rows.append(x)
    ids={r['dataset_id'] for r in rows}
    if len(rows)!=13 or len(ids)!=13:raise RuntimeError(('need 13 unique survey results',len(rows),sorted(ids)))
    gains=np.asarray([r['gain_sz3_over_ours'] for r in rows],float);rng=np.random.default_rng(20260814);boots=np.empty(20000,float)
    for i in range(boots.size):boots[i]=np.median(rng.choice(gains,size=len(gains),replace=True))
    headline={'survey_count':13,'win_rate':float(np.mean(gains>1.0)),'wins':int(np.sum(gains>1.0)),'median_gain':float(np.median(gains)),'bootstrap95_median_gain':[float(np.percentile(boots,2.5)),float(np.percentile(boots,97.5))],'p10_gain':percentile(gains,10),'byte_weighted_gain':sum(r['sz3_bytes'] for r in rows)/sum(r['ours_bytes'] for r in rows),'total_ours_bytes':int(sum(r['ours_bytes'] for r in rows)),'total_sz3_bytes':int(sum(r['sz3_bytes'] for r in rows))}
    headline['passes_preregistered_general_win']=bool(headline['win_rate']>=0.80 and headline['median_gain']>=1.20 and headline['bootstrap95_median_gain'][0]>1.0)
    groups={}
    for label,prefix in [('land','land-'),('marine','marine-'),('DAS','DAS-')]:
        rr=[r for r in rows if r['category'].startswith(prefix)];gg=np.asarray([r['gain_sz3_over_ours'] for r in rr],float);groups[label]={'n':len(rr),'wins':int(np.sum(gg>1)),'win_rate':float(np.mean(gg>1)),'median_gain':float(np.median(gg)),'byte_weighted_gain':sum(r['sz3_bytes'] for r in rr)/sum(r['ours_bytes'] for r in rr)} if rr else {'n':0}
    out={'benchmark':'general-seismic-benchmark-v1','portfolio':'general-seismic-codec-portfolio-v1','headline':headline,'groups':groups,'surveys':sorted(rows,key=lambda r:r['dataset_id'])};dump_json(out,args.out);print(json.dumps(out,indent=2));return out

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('survey');s.add_argument('--manifest',required=True);s.add_argument('--preflight',required=True);s.add_argument('--config',required=True);s.add_argument('--dataset',required=True);s.add_argument('--cube2mseed',default=os.environ.get('CUBE2MSEED'));s.add_argument('--out',required=True)
    a=sub.add_parser('aggregate');a.add_argument('--results',required=True);a.add_argument('--out',required=True)
    args=ap.parse_args();run_survey(args) if args.cmd=='survey' else aggregate(args)
if __name__=='__main__':main()
