import json, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import boto3
from botocore import UNSIGNED
from botocore.config import Config

TARGET = 10 * 1000**3
RANGE_BLOCK = 1024 * 1024
EXTS = {
    'SEG-Y': ('.sgy','.segy','.seg-y','.seg_y','.sgy.partaa','.sgy.partab','.sgy.partac','.sgy.partad','.sgy.partae'),
    'HDF5': ('.h5','.hdf5'),
    'HDF5/TDMS': ('.h5','.hdf5','.tdms'),
    'SEGD': ('.segd','.sgd','.seg-d'),
}

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED, retries={'max_attempts': 10}))

def parse_s3(uri):
    u=urlparse(uri)
    if u.scheme!='s3': raise ValueError(uri)
    return u.netloc, u.path.lstrip('/')

def canonical(o):
    return o['key'] + ('::' + o['member'] if o.get('member') else '')

def object_meta(uri):
    bucket,key=parse_s3(uri)
    r=s3.head_object(Bucket=bucket,Key=key)
    return {'bucket':bucket,'key':key,'size':int(r['ContentLength']),'uri':uri}

def list_objects(uri):
    bucket,prefix=parse_s3(uri)
    out=[]; token=None
    while True:
        kw={'Bucket':bucket,'Prefix':prefix,'MaxKeys':1000}
        if token: kw['ContinuationToken']=token
        r=s3.list_objects_v2(**kw)
        for o in r.get('Contents',[]):
            if int(o['Size'])>0: out.append({'bucket':bucket,'key':o['Key'],'size':int(o['Size']),'uri':f"s3://{bucket}/{o['Key']}"})
        if not r.get('IsTruncated'): break
        token=r['NextContinuationToken']
    out.sort(key=canonical)
    return out

def _parse_tar_num(raw):
    raw=raw.rstrip(b'\0 ').strip()
    if not raw:return 0
    if raw[0] & 0x80:
        return int.from_bytes(raw,'big',signed=True)
    return int(raw,8)

def _tar_name(h):
    name=h[0:100].split(b'\0',1)[0].decode('utf-8','replace')
    prefix=h[345:500].split(b'\0',1)[0].decode('utf-8','replace')
    return (prefix+'/'+name) if prefix else name

def index_tar_waveforms(outer, member_pattern):
    bucket,key,total=outer['bucket'],outer['key'],int(outer['size'])
    rx=re.compile(member_pattern)
    out=[]; pos=0; cache_start=-1; cache=b''; longname=None
    while pos+512<=total:
        if not (cache_start <= pos and pos+512 <= cache_start+len(cache)):
            cache_start=pos
            end=min(total-1,pos+RANGE_BLOCK-1)
            cache=s3.get_object(Bucket=bucket,Key=key,Range=f'bytes={pos}-{end}')['Body'].read()
        off=pos-cache_start; h=cache[off:off+512]
        if len(h)<512: raise RuntimeError(('short TAR header',key,pos,len(h)))
        if not h.strip(b'\0'):break
        name=_tar_name(h); size=_parse_tar_num(h[124:136]); typ=h[156:157]
        if size<0:raise RuntimeError(('negative TAR member size',key,pos,name,size))
        data_off=pos+512
        if typ==b'L':
            # GNU long-name record: fetch the name payload, then apply it to the next entry.
            end=min(total-1,data_off+size-1)
            payload=s3.get_object(Bucket=bucket,Key=key,Range=f'bytes={data_off}-{end}')['Body'].read() if size else b''
            longname=payload.split(b'\0',1)[0].decode('utf-8','replace')
        elif typ in (b'0',b'\0'):
            if longname:
                name=longname; longname=None
            if rx.search(name):
                out.append({'bucket':bucket,'key':key,'member':name,'member_offset':data_off,'size':int(size),'uri':f"s3tar://{bucket}/{key}::{name}"})
        else:
            longname=None
        pos=data_off+((size+511)//512)*512
    return out

def _outer_filters(ds,objs):
    inc=ds.get('include_regex'); exc=ds.get('exclude_regex')
    if inc:
        rx=re.compile(inc);objs=[o for o in objs if rx.search(o['key'])]
    if exc:
        rx=re.compile(exc);objs=[o for o in objs if not rx.search(o['key'])]
    return objs

def resolve_objects(ds):
    explicit=ds.get('objects')
    if explicit:
        out=[object_meta(u) for u in explicit];out.sort(key=canonical);return out
    src=ds.get('source','')
    if not src.startswith('s3://'):
        raise RuntimeError('dataset has neither explicit S3 objects nor an S3 prefix')
    objs=list_objects(src)
    if ds.get('container_index')=='tar':
        outers=[o for o in _outer_filters(ds,objs) if o['key'].lower().endswith('.tar')]
        pat=ds.get('member_include_regex')
        if not pat:raise RuntimeError('tar container_index requires member_include_regex')
        members=[]
        # Tar archives are independent; scan them concurrently. Only 1 MiB header ranges
        # are read, never waveform payload, so selection remains cheap and signal-blind.
        with ThreadPoolExecutor(max_workers=min(16,max(1,len(outers)))) as ex:
            fut={ex.submit(index_tar_waveforms,o,pat):o for o in outers}
            for f in as_completed(fut):
                members.extend(f.result())
        members.sort(key=canonical)
        return members
    return objs

def eligible(ds, objs):
    inc=ds.get('include_regex'); exc=ds.get('exclude_regex')
    if inc and not ds.get('container_index'):
        rx=re.compile(inc);objs=[o for o in objs if rx.search(o['key'])]
    if exc and not ds.get('container_index'):
        rx=re.compile(exc);objs=[o for o in objs if not rx.search(o['key'])]
    minc=ds.get('member_include_regex')
    if minc:
        rx=re.compile(minc);return [o for o in objs if rx.search(o.get('member',''))]
    if ds.get('objects'):return objs
    fmt=ds.get('format','');exts=EXTS.get(fmt)
    if exts:
        q=[o for o in objs if o['key'].lower().endswith(exts)]
        if q:return q
    bad=('.txt','.md','.pdf','.png','.jpg','.jpeg','.json','.xml','.csv','.xlsx','.xls','.html','.htm','.sha256','.md5')
    return [o for o in objs if not o['key'].lower().endswith(bad)]

def spans(objs):
    if not objs:return []
    sizes=[o['size'] for o in objs];total=sum(sizes);cum=[];s=0
    for z in sizes:s+=z;cum.append(s)
    used=set();ans=[]
    for frac in (0.10,0.50,0.90):
        target=frac*total
        i=min(range(len(objs)),key=lambda j:abs((cum[j]-sizes[j]/2)-target));lo=hi=i;n=sizes[i]
        while n<TARGET and (lo>0 or hi+1<len(objs)):
            if lo>0 and hi+1<len(objs):
                lmid=cum[lo-1]-sizes[lo-1]/2;rmid=cum[hi+1]-sizes[hi+1]/2;take_left=abs(lmid-target)<=abs(rmid-target)
            else:take_left=lo>0
            if take_left:lo-=1;n+=objs[lo]['size']
            else:hi+=1;n+=objs[hi]['size']
        inds=list(range(lo,hi+1))
        if any(j in used for j in inds):
            candidates=[(abs((cum[j]-sizes[j]/2)-target),j) for j in range(len(objs)) if j not in used]
            if candidates:
                _,i=min(candidates);lo=hi=i;n=sizes[i]
                while n<TARGET and (lo>0 or hi+1<len(objs)):
                    choices=[]
                    if lo>0 and lo-1 not in used:choices.append((abs((cum[lo-1]-sizes[lo-1]/2)-target),'L'))
                    if hi+1<len(objs) and hi+1 not in used:choices.append((abs((cum[hi+1]-sizes[hi+1]/2)-target),'R'))
                    if not choices:break
                    _,side=min(choices)
                    if side=='L':lo-=1;n+=objs[lo]['size']
                    else:hi+=1;n+=objs[hi]['size']
                inds=list(range(lo,hi+1))
        used.update(inds);sel=[objs[j] for j in inds]
        ans.append({'center_fraction':frac,'bytes':sum(o['size'] for o in sel),'gb':sum(o['size'] for o in sel)/1e9,'objects':sel})
    return ans

def main(manifest):
    m=json.load(open(manifest));rows=[]
    for ds in m['datasets']:
        row={'id':ds['id'],'category':ds['category'],'format':ds['format'],'source':ds.get('source'),'explicit_objects':len(ds.get('objects',[]))}
        try:
            objs=eligible(ds,resolve_objects(ds));total=sum(o['size'] for o in objs)
            row.update(status='ok' if objs else 'empty',eligible_objects=len(objs),eligible_bytes=total,eligible_gb=total/1e9)
            if ds['source_size_gb']<=25:row['selected']=[{'center_fraction':None,'bytes':total,'gb':total/1e9,'objects':objs}]
            else:row['selected']=spans(objs)
            row['selected_bytes']=sum(x['bytes'] for x in row.get('selected',[]));row['selected_gb']=row['selected_bytes']/1e9
            min_gb=float(m['selection_policy']['minimum_primary_test_size_gb'])
            if row['selected_gb']+1e-9<min_gb:
                row['status']='too_small';row['error']=f"selected payload {row['selected_gb']:.3f} GB is below frozen minimum {min_gb} GB"
        except Exception as e:row.update(status='error',error=repr(e))
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='selected'}),flush=True)
    out={'benchmark':m['name'],'frozen':m['frozen'],'target_span_bytes':TARGET,'datasets':rows};json.dump(out,open('general_seismic_v1_preflight.json','w'),indent=2)
    bad=[r for r in rows if r['status']!='ok'];print(json.dumps({'ok':sum(r['status']=='ok' for r in rows),'bad':len(bad),'selected_gb':sum(r.get('selected_gb',0) for r in rows)},indent=2))
    if bad:sys.exit(2)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'benchmarks/general_seismic_v1.json')
