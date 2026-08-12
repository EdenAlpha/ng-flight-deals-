import json, os, struct, sys
import numpy as np

# Reuse the exact audited standalone container implementation from PR #136.
src=open('research/forge_standalone_segc.py').read().split("\nif __name__=='__main__':")[0]
exec(compile(src,'forge_standalone_segc.py','exec'),globals())


def encode_lattice_at_eps(inp,outp,public_eps):
    raw=open(inp,'rb').read();X,gx,gy,sx,sy,offs,layout=load_segy(inp);ntr,ns=X.shape
    gh,H=split_headers(raw,ntr,ns);hb=encode_headers(gh,H);sb,smeta=encode_samples(X,gx,gy,sx,sy,offs,float(public_eps))
    blob=struct.pack(FILE_HDR,FILE_MAGIC,1,ntr,ns,int(layout['dt_us']),5,len(raw),len(hb),len(sb))+hb+sb
    open(outp,'wb').write(blob)
    return {'input_bytes':len(raw),'container_bytes':len(blob),'whole_file_ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(sb),'public_eps':float(public_eps),'sample':smeta,'layout':layout}


def encode_sz3_at_eps(inp,outp,public_eps):
    raw=open(inp,'rb').read();X,gx,gy,sx,sy,offs,layout=load_segy(inp);gh,H=split_headers(raw,*X.shape);hb=encode_headers(gh,H);best,ordlist=best_sz3_blob(X,gx,gy,sx,sy,offs,float(public_eps));bb=best[3]
    blob=struct.pack(BASE_HDR,BASE_MAGIC,1,X.shape[0],X.shape[1],float(public_eps),best[2],len(hb),len(bb))+hb+bb
    open(outp,'wb').write(blob)
    return {'container_bytes':len(blob),'whole_file_ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(bb),'order':best[1],'order_code':best[2],'maxerr_ordered':best[4]}


def run_frac(inp,frac):
    X,*_=load_segy(inp);std=float(X.astype(np.float64).std());eps=float(frac)*std
    tag=str(frac).replace('.','p')
    lp=f'utah_{tag}.segc';lr=f'utah_{tag}_recon.sgy';sp=f'utah_{tag}.segz';sr=f'utah_{tag}_sz3_recon.sgy'
    enc=encode_lattice_at_eps(inp,lp,eps);dec=decode_segc(lp,lr);ver=verify(inp,lr,eps)
    base=encode_sz3_at_eps(inp,sp,eps);decode_sz3_container(sp,sr,enc['input_bytes']);bver=verify(inp,sr,eps)
    out={'fraction_sigma':float(frac),'std':std,'eps':eps,'lattice':enc,'lattice_decode':dec,'lattice_verify':ver,'sz3':base,'sz3_verify':bver,'whole_file_size_gain':base['container_bytes']/enc['container_bytes']}
    for p in (lr,sr,lp,sp):
        try: os.remove(p)
        except FileNotFoundError: pass
    return out


def main(inp):
    fracs=[0.01,0.02,0.05,0.10];rows=[]
    for f in fracs:
        print('FIDELITY',f,flush=True);r=run_frac(inp,f);rows.append(r)
        print(json.dumps({'fraction_sigma':f,'eps':r['eps'],'lattice_ratio':r['lattice']['whole_file_ratio'],'sz3_ratio':r['sz3']['whole_file_ratio'],'gain':r['whole_file_size_gain'],'lattice_bytes':r['lattice']['container_bytes'],'sample_bytes':r['lattice']['sample_blob_bytes'],'valid':r['lattice_verify']['valid']},indent=2),flush=True)
    out={'file':os.path.basename(inp),'rows':rows};json.dump(out,open('forge_standalone_fidelity.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
