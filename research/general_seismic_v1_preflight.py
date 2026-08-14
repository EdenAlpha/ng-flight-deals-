import json, os, re, sys
from urllib.parse import urlparse

import boto3
from botocore import UNSIGNED
from botocore.config import Config

TARGET = 10 * 1000**3
EXTS = {
    'SEG-Y': ('.sgy','.segy','.seg-y','.seg_y'),
    'HDF5': ('.h5','.hdf5'),
    'HDF5/TDMS': ('.h5','.hdf5','.tdms'),
    'SEGD': ('.segd','.sgd','.seg-d'),
}

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED, retries={'max_attempts': 10}))

def parse_s3(uri):
    u=urlparse(uri)
    if u.scheme!='s3': raise ValueError(uri)
    return u.netloc, u.path.lstrip('/')

def list_objects(uri):
    bucket,prefix=parse_s3(uri)
    out=[]; token=None
    while True:
        kw={'Bucket':bucket,'Prefix':prefix,'MaxKeys':1000}
        if token: kw['ContinuationToken']=token
        r=s3.list_objects_v2(**kw)
        for o in r.get('Contents',[]):
            if int(o['Size'])>0: out.append({'bucket':bucket,'key':o['Key'],'size':int(o['Size'])})
        if not r.get('IsTruncated'): break
        token=r['NextContinuationToken']
    out.sort(key=lambda x:x['key'])
    return out

def eligible(ds, objs):
    fmt=ds.get('format','')
    exts=EXTS.get(fmt)
    if exts:
        q=[o for o in objs if o['key'].lower().endswith(exts)]
        if q: return q
    # For mixed/custom raw formats, retain all non-obvious metadata/archive auxiliaries.
    bad=('.txt','.md','.pdf','.png','.jpg','.jpeg','.json','.xml','.csv','.xlsx','.xls','.html','.htm','.sha256','.md5')
    return [o for o in objs if not o['key'].lower().endswith(bad)]

def spans(objs):
    if not objs: return []
    sizes=[o['size'] for o in objs]; total=sum(sizes)
    cum=[]; s=0
    for z in sizes: s+=z; cum.append(s)
    used=set(); ans=[]
    for frac in (0.10,0.50,0.90):
        target=frac*total
        i=min(range(len(objs)), key=lambda j:abs((cum[j]-sizes[j]/2)-target))
        lo=hi=i; n=sizes[i]
        while n<TARGET and (lo>0 or hi+1<len(objs)):
            left=objs[lo-1]['size'] if lo>0 else -1
            right=objs[hi+1]['size'] if hi+1<len(objs) else -1
            # deterministic: grow toward smaller cumulative-distance side; tie -> lexical/left
            if lo>0 and hi+1<len(objs):
                lmid=(cum[lo-1]-sizes[lo-1]/2); rmid=(cum[hi+1]-sizes[hi+1]/2)
                take_left=abs(lmid-target)<=abs(rmid-target)
            else: take_left=lo>0
            if take_left: lo-=1; n+=objs[lo]['size']
            else: hi+=1; n+=objs[hi]['size']
        inds=list(range(lo,hi+1))
        overlap=[j for j in inds if j in used]
        # If a span overlaps a prior span, walk outward deterministically until disjoint when possible.
        if overlap:
            candidates=[]
            for j in range(len(objs)):
                if j not in used: candidates.append((abs((cum[j]-sizes[j]/2)-target),j))
            if candidates:
                _,i=min(candidates); lo=hi=i; n=sizes[i]
                while n<TARGET and (lo>0 or hi+1<len(objs)):
                    choices=[]
                    if lo>0 and lo-1 not in used: choices.append((abs((cum[lo-1]-sizes[lo-1]/2)-target),'L'))
                    if hi+1<len(objs) and hi+1 not in used: choices.append((abs((cum[hi+1]-sizes[hi+1]/2)-target),'R'))
                    if not choices: break
                    _,side=min(choices)
                    if side=='L': lo-=1; n+=objs[lo]['size']
                    else: hi+=1; n+=objs[hi]['size']
                inds=list(range(lo,hi+1))
        used.update(inds)
        sel=[objs[j] for j in inds]
        ans.append({'center_fraction':frac,'bytes':sum(o['size'] for o in sel),'gb':sum(o['size'] for o in sel)/1e9,'objects':sel})
    return ans

def main(manifest):
    m=json.load(open(manifest)); rows=[]
    for ds in m['datasets']:
        src=ds['source']; row={'id':ds['id'],'category':ds['category'],'format':ds['format'],'source':src}
        if not src.startswith('s3://'):
            row.update(status='unresolved_non_s3_source', reason='manifest source is descriptive/non-S3 and must be replaced by exact downloadable objects before execution')
            rows.append(row); print(json.dumps(row),flush=True); continue
        try:
            objs=eligible(ds,list_objects(src)); total=sum(o['size'] for o in objs)
            row.update(status='ok' if objs else 'empty', eligible_objects=len(objs), eligible_bytes=total, eligible_gb=total/1e9)
            if ds['source_size_gb']<=25:
                row['selected']=[{'center_fraction':None,'bytes':total,'gb':total/1e9,'objects':objs}]
            else:
                row['selected']=spans(objs)
            row['selected_bytes']=sum(x['bytes'] for x in row.get('selected',[])); row['selected_gb']=row['selected_bytes']/1e9
        except Exception as e:
            row.update(status='error',error=repr(e))
        rows.append(row); print(json.dumps({k:v for k,v in row.items() if k!='selected'}),flush=True)
    out={'benchmark':m['name'],'frozen':m['frozen'],'target_span_bytes':TARGET,'datasets':rows}
    json.dump(out,open('general_seismic_v1_preflight.json','w'),indent=2)
    bad=[r for r in rows if r['status'] not in ('ok','unresolved_non_s3_source')]
    print(json.dumps({'ok':sum(r['status']=='ok' for r in rows),'unresolved':sum(r['status']=='unresolved_non_s3_source' for r in rows),'bad':len(bad)},indent=2))
    if bad: sys.exit(2)

if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else 'benchmarks/general_seismic_v1.json')
