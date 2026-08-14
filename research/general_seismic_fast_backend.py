import numpy as np


def install(codec_module):
    """Replace only ZSM arithmetic hot loops with the bit-exact compiled backend."""
    import general_seismic_fast_zsm as fast
    py_enc=codec_module.encode_zsm
    py_dec=codec_module.decode_zsm
    def enc(K,W):
        return fast.encode_zsm(np.ascontiguousarray(K,dtype=np.int32),int(W))
    def dec(bb,nbit,W,shape):
        nr,nt=map(int,shape)
        return fast.decode_zsm(bb,int(nbit),int(W),nr,nt)
    codec_module._reference_encode_zsm=py_enc
    codec_module._reference_decode_zsm=py_dec
    codec_module.encode_zsm=enc
    codec_module.decode_zsm=dec
    return codec_module


def equivalence(codec_module, fast_module, seed=24680):
    rng=np.random.default_rng(seed)
    cases=[]
    for shape in ((7,257),(32,1024),(128,4096)):
        K=rng.integers(-9,10,size=shape,dtype=np.int32)
        K[rng.random(shape)<0.68]=0
        for W in (4,8,64):
            a,na=codec_module.encode_zsm(K,W)
            b,nb=fast_module.encode_zsm(K,W)
            if na!=nb or a!=b:
                raise AssertionError(('encoded stream mismatch',shape,W,len(a),len(b),na,nb))
            da=codec_module.decode_zsm(a,na,W,shape)
            db=fast_module.decode_zsm(b,nb,W,*shape)
            if not np.array_equal(da,K) or not np.array_equal(db,K) or not np.array_equal(da,db):
                raise AssertionError(('decode mismatch',shape,W))
            cases.append({'shape':list(shape),'W':W,'bytes':len(a),'bits':int(na)})
    return cases
