import json,numpy as np
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);N=q.size

def H(a):
    if len(a)==0:return 0.0
    _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def H1(a):
    if len(a)<2:return 0.0
    vals,s=np.unique(a,return_inverse=True);m=len(vals);s=s.astype(np.int64)
    pc=np.bincount(s[:-1]*m+s[1:],minlength=m*m); pp=np.bincount(s[:-1],minlength=m)
    def hc(c):c=c[c>0].astype(float);p=c/c.sum();return float(-(p*np.log2(p)).sum())
    return hc(pc)-hc(pp)
ends=[]
for line in open('hpez_level_ends.txt'):
    lev,e=line.split();ends.append((int(lev),int(e)))
segments=[];st=0
for lev,e in ends:
    a=q[st:e];segments.append({'level':lev,'start':st,'end':e,'n':len(a),'H0':H(a),'H1':H1(a),'center_frac':float(np.mean(a==32768)),'same_frac':float(np.mean(a[1:]==a[:-1])) if len(a)>1 else 0});st=e
if st<N:
    a=q[st:];segments.append({'level':'tail','start':st,'end':N,'n':len(a),'H0':H(a),'H1':H1(a),'center_frac':float(np.mean(a==32768)),'same_frac':float(np.mean(a[1:]==a[:-1])) if len(a)>1 else 0})
weighted_H0=sum(x['n']*x['H0'] for x in segments)/N
weighted_H1=sum(x['n']*x['H1'] for x in segments)/N
out={'N':int(N),'ends':ends,'segments':segments,'H0_given_level_bps':weighted_H0,'H1_given_level_bps':weighted_H1,'ideal_H0_given_level_bytes':weighted_H0*N/8,'ideal_H1_given_level_bytes':weighted_H1*N/8}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_level_analysis.json','w'),indent=2)
