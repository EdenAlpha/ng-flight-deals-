import sys,json
import imperial_ar8_adaptive_context_address as a

a.P=1
a.TRAIN=64

def main(path):
    a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_adaptive_context_address.json'
    d=json.load(open(src));d['scope']=d['scope'].replace('PR564 AR8/step267 champion','AR1/train64/step267 coordinate system').replace('charged AR8 model','charged AR1 model')
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'ar1_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
