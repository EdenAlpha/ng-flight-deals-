import sys,json
import imperial_ar4_rich_adaptive_context_address as r

r.a.P=1
r.a.TRAIN=64

def main(path):
    # r's import already installs the richer decoder-known context grammar.
    r.a.main(path)
    src='imperial_ar8_adaptive_context_address.json';dst='imperial_ar1_rich_adaptive_context_address.json'
    d=json.load(open(src))
    d['order']=1;d['train']=64
    d['scope']='Exact AR1/train64/step267 hybrid restricted address using the richer decoder-shared causal context grammar proven in PR600. The coordinate model is the best exact rank-only configuration from PR586 (AR1 trained on the first 64 samples). Existing combinatorial rank and all adaptive context candidates compete per bitplane. Adaptive state is derived only from already decoded higher planes and same-plane causal history; no learned probability table or context counts are transmitted. The AR1 float32 model, public configuration selector, family tags, and every physical arithmetic byte are charged. Full K decode, causal AR1 replay, and the unchanged source hard-error bound are mandatory.'
    json.dump(d,open(dst,'w'),indent=2)
    print(json.dumps({'ar1_rich_summary':{'bytes':d['hybrid']['bytes'],'payload_bytes':d['hybrid']['payload_bytes'],'rank_floor':d['rank_floor']['bytes'],'model_bytes':d['model_bytes'],'old_ar32':d['old_ar32']['bytes'],'sz3':d['sz3']['bytes'],'gain_vs_old_ar32':d['old_ar32']['bytes']/d['hybrid']['bytes'],'gain_vs_sz3':d['sz3']['bytes']/d['hybrid']['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
