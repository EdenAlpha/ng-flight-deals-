from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
# Record cumulative quantization-symbol boundaries for the committed (non-tuning) pass.
needle='''                if(tuning){\n                    conf.quant_bin_counts[level-1]=quant_inds.size();\n                }\n            }                    \n            //timer.start();'''
repl='''                if(tuning){\n                    conf.quant_bin_counts[level-1]=quant_inds.size();\n                }\n                else {\n                    FILE *lf=std::fopen("hpez_level_ends.txt", level==start_level ? "w" : "a");\n                    if(lf){std::fprintf(lf,"%u %zu\\n",level,quant_inds.size());std::fclose(lf);}\n                }\n            }                    \n            //timer.start();'''
if needle not in s: raise SystemExit('level-end needle missing')
s=s.replace(needle,repl,1)
p.write_text(s)
print('patched level boundaries')
