#!/usr/bin/env python3
import hashlib,os,sys,boto3
from botocore import UNSIGNED
from botocore.config import Config
out=sys.argv[1] if len(sys.argv)>1 else 'imperial.h5'
s=boto3.client('s3',config=Config(signature_version=UNSIGNED))
s.download_file('gdr-data-lake','imperialvalleydas/v1.0.0/DF__UTC_20201113_235932.602.h5',out)
assert os.path.getsize(out)==415030456
assert hashlib.md5(open(out,'rb').read()).hexdigest()=='8cb7ea8466ab48880f876fc43cb5ce75'
