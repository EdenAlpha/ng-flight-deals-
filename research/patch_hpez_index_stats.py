from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
s=s.replace('#include <limits>', '#include <limits>\n#include <cstdio>',1)
needle='''            quantizer.save(buffer_pos);'''
stats='''            {\n                const size_t qn=quant_inds.size();\n                const int rad=quantizer.get_radius();\n                std::vector<unsigned long long> hh((size_t)rad*2+1,0);\n                unsigned long long same=0;\n                for(size_t qi=0;qi<qn;qi++){int v=quant_inds[qi];if(v>=0 && (size_t)v<hh.size())hh[(size_t)v]++;if(qi && quant_inds[qi]==quant_inds[qi-1])same++;}\n                double H=0;for(auto c:hh)if(c){double p=(double)c/qn;H-=p*std::log2(p);}\n                double fzero=qn?(double)hh[0]/qn:0;\n                double fcenter=(qn && rad<(int)hh.size())?(double)hh[(size_t)rad]/qn:0;\n                double fsame=qn>1?(double)same/(qn-1):0;\n                std::fprintf(stderr,"HPEZIDX n=%zu H=%.12g ideal_bytes=%.3f unpred_frac=%.12g center_frac=%.12g same_frac=%.12g unpred_bytes=%zu\\n",qn,H,H*qn/8.0,fzero,fcenter,fsame,quantizer.size_est());\n            }\n            quantizer.save(buffer_pos);'''
if needle not in s: raise SystemExit('quantizer.save missing')
s=s.replace(needle,stats)
# Capture bytes after HPEZ's entropy encoder, before the final zstd stage.
s=s.replace('''            assert(buffer_pos - buffer < bufferSize);         \n            uchar *lossless_data = lossless.compress(buffer,''','''            assert(buffer_pos - buffer < bufferSize);\n            std::fprintf(stderr,"HPEZPRELOSSLESS bytes=%zu\\n",(size_t)(buffer_pos-buffer));\n            uchar *lossless_data = lossless.compress(buffer,''')
s=s.replace('''            assert(buffer_pos - buffer < bufferSize);\n            //timer.start();\n            uchar *lossless_data = lossless.compress(buffer,''','''            assert(buffer_pos - buffer < bufferSize);\n            std::fprintf(stderr,"HPEZPRELOSSLESS bytes=%zu\\n",(size_t)(buffer_pos-buffer));\n            //timer.start();\n            uchar *lossless_data = lossless.compress(buffer,''')
p.write_text(s)
print('instrumented index statistics')
