#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>

namespace py = pybind11;

static constexpr uint32_t MAXV = 0xffffffffu;
static constexpr uint32_t HALF = 0x80000000u;
static constexpr uint32_t Q1   = 0x40000000u;
static constexpr uint32_t Q3   = 0xc0000000u;
static constexpr int Z_NZERO=9*9*6;
static constexpr int Z_NSIGN=3*3*6;
static constexpr int Z_NPREF=6*6*16;
static constexpr int Z_NSUFF=16*16*6;
static constexpr int OFF_SIGN=Z_NZERO;
static constexpr int OFF_PREF=OFF_SIGN+Z_NSIGN;
static constexpr int OFF_SUFF=OFF_PREF+Z_NPREF;
static constexpr int NCTX=OFF_SUFF+Z_NSUFF;

struct BitWriter {
    std::string bytes;
    uint64_t nbit=0;
    void put(int b){
        if((nbit & 7u)==0) bytes.push_back(char(0));
        if(b) bytes.back() = char(uint8_t(bytes.back()) | uint8_t(1u << (7u-(nbit&7u))));
        ++nbit;
    }
};

struct BitReader {
    const std::string &bytes;
    uint64_t nbit, pos=0;
    BitReader(const std::string &b, uint64_t n): bytes(b),nbit(n){}
    int get(){
        if(pos>=nbit) return 0;
        uint8_t z=uint8_t(bytes[size_t(pos>>3)]);
        int b=(z>>(7u-(pos&7u)))&1u; ++pos; return b;
    }
};

static inline int clip4(int64_t x){ if(x<-4)x=-4; if(x>4)x=4; return int(x)+4; }
static inline int ac_state(int64_t sumabs,int count){
    if(count<=0) return 0;
    int64_t z=2*sumabs;
    static constexpr int q[5]={1,3,7,15,31};
    for(int i=0;i<5;++i) if(z<=int64_t(q[i])*count) return i;
    return 5;
}
static inline int sgncat(int64_t x){return x<0?0:(x>0?2:1);}
static inline int magbin(int64_t x){
    uint64_t m=x<0?uint64_t(-x):uint64_t(x);
    if(m==0)return 0; if(m==1)return 1; if(m==2)return 2; if(m<=4)return 3; if(m<=8)return 4; return 5;
}
static inline int zero_ctx(int64_t prev,int64_t left,int ac){return ((clip4(prev)*9+clip4(left))*6+ac);}
static inline int sign_ctx(int64_t prev,int64_t left,int ac){return OFF_SIGN+((sgncat(prev)*3+sgncat(left))*6+ac);}
static inline int pref_ctx(int64_t prev,int ac,int qpos){return OFF_PREF+((magbin(prev)*6+ac)*16+std::min(qpos,15));}
static inline int suff_ctx(int q,int bitpos,int ac){return OFF_SUFF+((std::min(q,15)*16+std::min(bitpos,15))*6+ac);}

struct ArithmeticEncoder {
    uint32_t lo=0, hi=MAXV;
    uint64_t pending=0;
    BitWriter out;
    std::vector<std::array<int32_t,2>> c;
    ArithmeticEncoder():c(NCTX){for(auto &x:c){x[0]=1;x[1]=1;}}
    void emit(int b){out.put(b); for(uint64_t i=0;i<pending;++i)out.put(1-b); pending=0;}
    void put(int b,int ctx){
        int64_t c0=c[ctx][0], c1=c[ctx][1], tot=c0+c1;
        uint64_t rng=uint64_t(hi)-uint64_t(lo)+1ull;
        uint32_t sp=uint32_t(uint64_t(lo)+(rng*uint64_t(c0))/uint64_t(tot)-1ull);
        if(b==0) hi=sp; else lo=sp+1u;
        while(true){
            if(hi<HALF) emit(0);
            else if(lo>=HALF){emit(1);lo-=HALF;hi-=HALF;}
            else if(lo>=Q1 && hi<Q3){++pending;lo-=Q1;hi-=Q1;}
            else break;
            lo=uint32_t(lo<<1); hi=uint32_t((hi<<1)|1u);
        }
        ++c[ctx][b];
        if(int64_t(c[ctx][0])+c[ctx][1]>16384){c[ctx][0]=(c[ctx][0]+1)/2;c[ctx][1]=(c[ctx][1]+1)/2;}
    }
    py::tuple finish(){++pending;emit(lo<Q1?0:1);return py::make_tuple(py::bytes(out.bytes),py::int_(out.nbit));}
};

struct ArithmeticDecoder {
    uint32_t lo=0,hi=MAXV,v=0;
    BitReader in;
    std::vector<std::array<int32_t,2>> c;
    ArithmeticDecoder(const std::string &b,uint64_t n):in(b,n),c(NCTX){
        for(auto &x:c){x[0]=1;x[1]=1;}
        for(int i=0;i<32;++i)v=uint32_t((v<<1)|uint32_t(in.get()));
    }
    int get(int ctx){
        int64_t c0=c[ctx][0], c1=c[ctx][1],tot=c0+c1;
        uint64_t rng=uint64_t(hi)-uint64_t(lo)+1ull;
        uint32_t sp=uint32_t(uint64_t(lo)+(rng*uint64_t(c0))/uint64_t(tot)-1ull);
        int b;
        if(v<=sp){b=0;hi=sp;}else{b=1;lo=sp+1u;}
        while(true){
            if(hi<HALF){}
            else if(lo>=HALF){lo-=HALF;hi-=HALF;v-=HALF;}
            else if(lo>=Q1 && hi<Q3){lo-=Q1;hi-=Q1;v-=Q1;}
            else break;
            lo=uint32_t(lo<<1);hi=uint32_t((hi<<1)|1u);v=uint32_t((v<<1)|uint32_t(in.get()));
        }
        ++c[ctx][b];
        if(int64_t(c[ctx][0])+c[ctx][1]>16384){c[ctx][0]=(c[ctx][0]+1)/2;c[ctx][1]=(c[ctx][1]+1)/2;}
        return b;
    }
};

py::tuple encode_zsm(py::array_t<int32_t,py::array::c_style|py::array::forcecast> arr,int W){
    if(arr.ndim()!=2)throw std::runtime_error("K must be 2D");
    if(W<=0)throw std::runtime_error("W must be positive");
    ssize_t nr=arr.shape(0),nt=arr.shape(1); auto K=arr.unchecked<2>();
    ArithmeticEncoder E;
    std::vector<int64_t> ring(size_t(nr)*size_t(W),0),sums(size_t(nr),0);
    for(ssize_t t=0;t<nt;++t){
        int rp=int(t%W),cnt=int(std::min<ssize_t>(t,W));
        for(ssize_t cc=0;cc<nr;++cc){
            int ac=ac_state(sums[size_t(cc)],cnt);
            int64_t prev=t?int64_t(K(cc,t-1)):0;
            int64_t left=cc?int64_t(K(cc-1,t)):0;
            int64_t k=int64_t(K(cc,t)); int iszero=(k==0)?1:0;
            E.put(iszero,zero_ctx(prev,left,ac));
            if(!iszero){
                E.put(k<0?1:0,sign_ctx(prev,left,ac));
                uint64_t mag=k<0?uint64_t(-k):uint64_t(k); int q=0; for(uint64_t z=mag;z>1;z>>=1)++q;
                for(int j=0;j<q;++j)E.put(0,pref_ctx(prev,ac,j));
                E.put(1,pref_ctx(prev,ac,q));
                uint64_t rem=mag-(uint64_t(1)<<q);
                for(int bp=q-1;bp>=0;--bp)E.put(int((rem>>bp)&1ull),suff_ctx(q,q-1-bp,ac));
            }
            size_t ix=size_t(cc)*size_t(W)+size_t(rp);int64_t old=ring[ix];int64_t neu=k<0?-k:k;ring[ix]=neu;sums[size_t(cc)]+=neu-old;
        }
    }
    return E.finish();
}

py::array_t<int32_t> decode_zsm(py::bytes bb,uint64_t nbit,int W,ssize_t nr,ssize_t nt){
    if(W<=0||nr<0||nt<0)throw std::runtime_error("bad decode dimensions");
    std::string b=bb;
    py::array_t<int32_t> out({nr,nt});auto K=out.mutable_unchecked<2>();
    ArithmeticDecoder D(b,nbit);
    std::vector<int64_t> ring(size_t(nr)*size_t(W),0),sums(size_t(nr),0);
    for(ssize_t t=0;t<nt;++t){
        int rp=int(t%W),cnt=int(std::min<ssize_t>(t,W));
        for(ssize_t cc=0;cc<nr;++cc){
            int ac=ac_state(sums[size_t(cc)],cnt);int64_t prev=t?int64_t(K(cc,t-1)):0;int64_t left=cc?int64_t(K(cc-1,t)):0;
            int iszero=D.get(zero_ctx(prev,left,ac));int64_t k=0;
            if(!iszero){
                int neg=D.get(sign_ctx(prev,left,ac));int q=0;
                while(true){int bit=D.get(pref_ctx(prev,ac,q));if(bit)break;++q;if(q>30)throw std::runtime_error("gamma overflow");}
                uint64_t rem=0;for(int pos=0;pos<q;++pos)rem=(rem<<1)|uint64_t(D.get(suff_ctx(q,pos,ac)));
                uint64_t mag=(uint64_t(1)<<q)+rem;k=neg?-int64_t(mag):int64_t(mag);
            }
            if(k<int64_t(INT32_MIN)||k>int64_t(INT32_MAX))throw std::runtime_error("decoded int32 overflow");
            K(cc,t)=int32_t(k);size_t ix=size_t(cc)*size_t(W)+size_t(rp);int64_t old=ring[ix];int64_t neu=k<0?-k:k;ring[ix]=neu;sums[size_t(cc)]+=neu-old;
        }
    }
    return out;
}

PYBIND11_MODULE(general_seismic_fast_zsm,m){
    m.doc()="Bit-exact compiled backend for general seismic ZSM arithmetic coding";
    m.def("encode_zsm",&encode_zsm,py::arg("K"),py::arg("W"));
    m.def("decode_zsm",&decode_zsm,py::arg("bytes"),py::arg("nbit"),py::arg("W"),py::arg("nr"),py::arg("nt"));
}
