import json,sys
import boto3
from botocore import UNSIGNED
from botocore.config import Config

S3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10}))

def tar_prefix_members(bucket,key,nbytes=64*1024*1024,max_members=32):
    r=S3.get_object(Bucket=bucket,Key=key,Range=f'bytes=0-{int(nbytes)-1}')
    b=r['Body'].read();out=[];pos=0
    while pos+512<=len(b) and len(out)<int(max_members):
        h=b[pos:pos+512]
        if not h.strip(b'\0'):break
        name=h[0:100].split(b'\0',1)[0].decode('utf-8','replace')
        prefix=h[345:500].split(b'\0',1)[0].decode('utf-8','replace')
        if prefix:name=prefix+'/'+name
        raw=h[124:136].rstrip(b'\0 ').strip()
        try:size=int(raw or b'0',8)
        except Exception:size=-1
        typ=h[156:157].decode('ascii','replace')
        out.append({'name':name,'size':size,'typeflag':typ,'header_offset':pos})
        if size<0:break
        nxt=pos+512+((size+511)//512)*512
        if nxt<=pos or nxt>len(b):break
        pos=nxt
    return {'range_bytes':len(b),'members':out}

def h5_schema_s3(bucket,key,max_items=80):
    import s3fs,h5py,numpy as np
    fs=s3fs.S3FileSystem(anon=True)
    out=[]
    with fs.open(f'{bucket}/{key}','rb',block_size=8*1024*1024) as fh:
      with h5py.File(fh,'r') as f:
        def visit(name,obj):
          if len(out)>=max_items:return
          if isinstance(obj,h5py.Dataset):
            out.append({'path':'/'+name,'shape':[int(x) for x in obj.shape],'dtype':str(obj.dtype),'chunks':None if obj.chunks is None else [int(x) for x in obj.chunks],'numeric':bool(np.issubdtype(obj.dtype,np.number))})
        f.visititems(visit)
    return out

def try_segd(path):
    attempts=[]
    try:
      from pysegd3.readsegd3 import read_segd_rev3
      it=read_segd_rev3(path);h,x=next(it)
      import numpy as np
      a=np.asarray(x)
      attempts.append({'reader':'pysegd3.read_segd_rev3','ok':True,'trace_shape':list(a.shape),'dtype':str(a.dtype),'header_keys':sorted(map(str,h.keys()))[:50] if hasattr(h,'keys') else str(type(h))})
      return attempts
    except Exception as e:attempts.append({'reader':'pysegd3.read_segd_rev3','ok':False,'error':repr(e)})
    try:
      import pysegd
      attempts.append({'reader':'pysegd','ok':False,'error':'package imported; API discovery required','module_attrs':sorted([x for x in dir(pysegd) if not x.startswith('_')])[:100]})
    except Exception as e:attempts.append({'reader':'pysegd import','ok':False,'error':repr(e)})
    return attempts

def main(segd_path):
    bucket='gdr-data-lake'
    out={}
    out['san_emidio_datacube_tar']=tar_prefix_members(bucket,'wholescale/2021_seismic/WHOLESCALE_Data_seismic_2021_data_level0_datacube.tar')
    out['san_emidio_smartsolo_tar']=tar_prefix_members(bucket,'wholescale/2021_seismic/WHOLESCALE_Data_seismic_2021_data_level0_smartsolo_dccdata_453001427.tar')
    out['forge_h5']=h5_schema_s3(bucket,'FORGE/DAS/april_2024/Neubrex/16b_continuous/v1.0.0/16B_1_StrainRate_20240423T232232+0000_14914.h5')
    out['egs_h5']=h5_schema_s3(bucket,'egs_collab/experiment_2/DAS/Terra15/205505/UTC-YMD20220322-HMS182523.983/CollabExp2_velocity_UTC-YMD20220326-HMS133246.118_seq_00000006407.hdf5')
    out['crescent_segd']=try_segd(segd_path)
    json.dump(out,open('general_seismic_schema_probe.json','w'),indent=2)
    print(json.dumps(out,indent=2))
if __name__=='__main__':main(sys.argv[1])
