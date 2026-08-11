from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
needle='''            encoder.save(buffer_pos);\n            encoder.encode(quant_inds, buffer_pos);'''
repl='''            encoder.save(buffer_pos);\n            if(quant_inds.size() > 1000000){\n                FILE *qf=std::fopen("hpez_final_quant_inds.bin","wb");\n                if(qf){std::fwrite(quant_inds.data(),sizeof(int),quant_inds.size(),qf);std::fclose(qf);}\n            }\n            encoder.encode(quant_inds, buffer_pos);'''
if needle not in s: raise SystemExit('encoder sequence needle missing')
s=s.replace(needle,repl)
p.write_text(s)
print('patched final symbol dump')
