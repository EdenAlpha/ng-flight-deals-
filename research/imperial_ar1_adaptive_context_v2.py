import sys,json
import imperial_ar8_adaptive_context_address as a

a.P=1
a.TRAIN=64

a.ADAPT=(
'global','prefix','t','c','tc','prefix_t','prefix_tc','prefix_t2','tc_c4','tc_t8',
't2','t3','c2','diag','tcd','prefix_diag','prefix_tcd','prefix_t3','prefix_c2',
'tmod2','tmod4','cmod2','diagmod4','prefix_tmod2','prefix_tcmod2','prefix_diagmod4',
'prefix_known_t','prefix_known_c','prefix_known_tc','prefix_known_diag','run_t4','prefix_run_t4','linear2','prefix_linear2'
)

def key(known,B,bit,c,t,fam):
    prefix=int(known[c,t]>>(bit+1));nc,nt=B.shape
    pt=int(B[c,t-1]) if t>0 else 2
    pt2=int(B[c,t-2]) if t>1 else 2
    pt3=int(B[c,t-3]) if t>2 else 2
    pc=int(B[c-1,t]) if c>0 else 2
    pc2=int(B[c-2,t]) if c>1 else 2
    pd=int(B[c-1,t-1]) if c>0 and t>0 else 2
    if c>0:pl=int(B[c-1,t])
    elif t>0:pl=int(B[nc-1,t-1])
    else:pl=2
    if c>1:pl2=int(B[c-2,t])
    elif c==1 and t>0:pl2=int(B[nc-1,t-1])
    elif c==0 and t>0:pl2=int(B[nc-2,t-1]) if nc>1 else 2
    else:pl2=2
    if fam=='global':return 0
    if fam=='prefix':return prefix
    if fam=='t':return pt
    if fam=='c':return pc
    if fam=='tc':return pt*3+pc
    if fam=='prefix_t':return prefix*3+pt
    if fam=='prefix_tc':return prefix*9+pt*3+pc
    if fam=='prefix_t2':return prefix*9+pt*3+pt2
    if fam=='tc_c4':return (c*4//nc)*9+pt*3+pc
    if fam=='tc_t8':return (t*8//nt)*9+pt*3+pc
    if fam=='t2':return pt*3+pt2
    if fam=='t3':return pt*9+pt2*3+pt3
    if fam=='c2':return pc*3+pc2
    if fam=='diag':return pd
    if fam=='tcd':return pt*9+pc*3+pd
    if fam=='prefix_diag':return prefix*3+pd
    if fam=='prefix_tcd':return prefix*27+pt*9+pc*3+pd
    if fam=='prefix_t3':return prefix*27+pt*9+pt2*3+pt3
    if fam=='prefix_c2':return prefix*9+pc*3+pc2
    if fam=='tmod2':return (t&1)*3+pt
    if fam=='tmod4':return (t&3)*3+pt
    if fam=='cmod2':return (c&1)*3+pc
    if fam=='diagmod4':return ((t+c)&3)*9+pt*3+pc
    if fam=='prefix_tmod2':return prefix*6+(t&1)*3+pt
    if fam=='prefix_tcmod2':return prefix*36+(t&1)*18+(c&1)*9+pt*3+pc
    if fam=='prefix_diagmod4':return prefix*36+((t+c)&3)*9+pt*3+pc
    kt=int((known[c,t-1]>>(bit+1))&3) if t>0 else 4
    kc=int((known[c-1,t]>>(bit+1))&3) if c>0 else 4
    kd=int((known[c-1,t-1]>>(bit+1))&3) if c>0 and t>0 else 4
    if fam=='prefix_known_t':return prefix*5+kt
    if fam=='prefix_known_c':return prefix*5+kc
    if fam=='prefix_known_tc':return prefix*25+kt*5+kc
    if fam=='prefix_known_diag':return prefix*5+kd
    if fam in ('run_t4','prefix_run_t4'):
        if t==0:r=0
        else:
            v=int(B[c,t-1]);r=1
            j=t-2
            while j>=0 and r<4 and int(B[c,j])==v:r+=1;j-=1
            r=(v*4)+(r-1)
        return (prefix*8+r) if fam=='prefix_run_t4' else r
    if fam=='linear2':return pl*3+pl2
    if fam=='prefix_linear2':return prefix*9+pl*3+pl2
    raise ValueError(fam)

a.akey=key

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_adaptive_context_v2.json'
    d=json.load(open(src));d['scope']='AR1/train64/step267 decoder-real adaptive-context V2. The encoder searches an expanded public family of causal shared coordinate/context systems, including longer temporal/channel history, diagonals, coordinate modulo classes, higher-plane neighbor prefixes, run state and linear-scan history. Context state is generated solely from already decoded higher planes, already decoded same-plane symbols and public coordinates. No context probability table or source-trained side model is transmitted; every plane stores only its chosen public family tag plus its actual arithmetic stream. The exact K field is independently decoded and causally replayed through the fully charged AR1 model under the unchanged source hard-error bound.'
    d['adaptive_families']=list(a.ADAPT)
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'v2_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
