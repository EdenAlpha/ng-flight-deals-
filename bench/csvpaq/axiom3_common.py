def vi(n):
    if n < 0: raise ValueError('negative varint')
    o=bytearray()
    while True:
        b=n & 127; n >>= 7
        if n: o.append(b|128)
        else: o.append(b); return bytes(o)

def uv(b,p=0):
    n=0; s=0
    while True:
        if p>=len(b): raise ValueError('truncated varint')
        x=b[p]; p+=1; n |= (x&127)<<s
        if not x&128: return n,p
        s += 7
        if s>70: raise ValueError('varint too long')

def zz(n): return (n<<1) ^ (n>>63)
def uz(n): return (n>>1) ^ -(n&1)
def enc_svar(n): return vi(zz(n))
def dec_svar(b,p):
    x,p=uv(b,p); return uz(x),p
