from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
# Member coordinate sequence parallels quant_inds for one compression invocation.
s=s.replace('''        std::vector<int> quant_inds;\n        std::vector<bool> mark;''','''        std::vector<int> quant_inds;\n        std::vector<size_t> quant_coords;\n        std::vector<bool> mark;''',1)
# Reset/reserve on every compressor invocation, so tuning trials cannot contaminate a later committed pass.
s=s.replace('''            quant_inds.reserve(num_elements);\n            size_t interp_compressed_size = 0;''','''            quant_inds.reserve(num_elements);\n            quant_coords.clear(); quant_coords.reserve(num_elements);\n            size_t interp_compressed_size = 0;''',1)
# Direct first anchor/sample has flat index zero.
s=s.replace('''            if(!anchor){\n                quant_inds.push_back(quantizer.quantize_and_overwrite(*data, 0));''','''            if(!anchor){\n                quant_coords.push_back(0);\n                quant_inds.push_back(quantizer.quantize_and_overwrite(*data, 0));''',1)
# Actual quantize helper already receives exact flat sample index.
s=s.replace('''        inline void quantize(size_t idx, T &d, T pred) {\n\n                quant_inds.push_back(quantizer.quantize_and_overwrite(d, pred));''','''        inline void quantize(size_t idx, T &d, T pred) {\n                quant_coords.push_back(idx);\n                quant_inds.push_back(quantizer.quantize_and_overwrite(d, pred));''',1)
# Some actual paths go through mode 0 of interpolation() rather than quantize().
s=s.replace('''            else if(mode==0){\n                 quant_inds.push_back(quantizer.quantize_and_overwrite(d, pred));''','''            else if(mode==0){\n                 quant_coords.push_back(idx);\n                 quant_inds.push_back(quantizer.quantize_and_overwrite(d, pred));''',1)
# Dump only the full final field; sampled/tuning subcompressions are far smaller.
needle='''            if(quant_inds.size() > 1000000){\n                FILE *qf=std::fopen("hpez_final_quant_inds.bin","wb");\n                if(qf){std::fwrite(quant_inds.data(),sizeof(int),quant_inds.size(),qf);std::fclose(qf);}\n            }'''
repl='''            if(quant_inds.size() > 1000000){\n                FILE *qf=std::fopen("hpez_final_quant_inds.bin","wb");\n                if(qf){std::fwrite(quant_inds.data(),sizeof(int),quant_inds.size(),qf);std::fclose(qf);}\n                std::fprintf(stderr,"HPEZCOORD q=%zu coords=%zu\\n",quant_inds.size(),quant_coords.size());\n                if(quant_coords.size()==quant_inds.size()){\n                    FILE *cf=std::fopen("hpez_final_quant_coords_u64.bin","wb");\n                    if(cf){for(size_t v:quant_coords){uint64_t u=(uint64_t)v;std::fwrite(&u,sizeof(uint64_t),1,cf);}std::fclose(cf);}\n                }\n            }'''
if needle not in s: raise SystemExit('symbol dump block not found')
s=s.replace(needle,repl,1)
p.write_text(s)
print('patched coordinate dump')
