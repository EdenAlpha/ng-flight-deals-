from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
s=s.replace('''        std::vector<int> quant_inds;\n        std::vector<size_t> quant_coords;''','''        std::vector<int> quant_inds;\n        std::vector<size_t> quant_coords;\n        std::vector<double> quant_ebs;''',1)
s=s.replace('''            quant_coords.clear(); quant_coords.reserve(num_elements);''','''            quant_coords.clear(); quant_coords.reserve(num_elements);\n            quant_ebs.clear(); quant_ebs.reserve(num_elements);''',1)
# Every coordinate-push in the decoder-authoritative patch is immediately before consuming a symbol. Mirror it with current EB.
s=s.replace('''                quant_coords.push_back(0);\n                *decData = quantizer.recover(0, quant_inds[quant_index++]);''','''                quant_coords.push_back(0); quant_ebs.push_back(quantizer.get_eb());\n                *decData = quantizer.recover(0, quant_inds[quant_index++]);''',1)
s=s.replace('''            quant_coords.push_back(idx);\n            d = quantizer.recover(pred, quant_inds[quant_index++]);''','''            quant_coords.push_back(idx); quant_ebs.push_back(quantizer.get_eb());\n            d = quantizer.recover(pred, quant_inds[quant_index++]);''',1)
s=s.replace('''                quant_coords.push_back(idx);\n                d = quantizer.recover(pred, quant_inds[quant_index++]);''','''                quant_coords.push_back(idx); quant_ebs.push_back(quantizer.get_eb());\n                d = quantizer.recover(pred, quant_inds[quant_index++]);''',1)
# Anchor symbols: record NaN sentinel, because they are raw unpredictable values rather than fixed-accuracy lattice symbols.
s=s.replace('''                    quant_coords.push_back(x);\n                    decData[x]=quantizer.recover_unpred();''','''                    quant_coords.push_back(x); quant_ebs.push_back(std::numeric_limits<double>::quiet_NaN());\n                    decData[x]=quantizer.recover_unpred();''',1)
s=s.replace('''                        quant_coords.push_back(x*dimension_offsets[0]+y);\n                        decData[x*dimension_offsets[0]+y]=quantizer.recover_unpred();''','''                        quant_coords.push_back(x*dimension_offsets[0]+y); quant_ebs.push_back(std::numeric_limits<double>::quiet_NaN());\n                        decData[x*dimension_offsets[0]+y]=quantizer.recover_unpred();''',1)
s=s.replace('''                            quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z);\n                            decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z]=quantizer.recover_unpred();''','''                            quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z); quant_ebs.push_back(std::numeric_limits<double>::quiet_NaN());\n                            decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z]=quantizer.recover_unpred();''',1)
s=s.replace('''                                quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w);\n                                decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w]=quantizer.recover_unpred();''','''                                quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w); quant_ebs.push_back(std::numeric_limits<double>::quiet_NaN());\n                                decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w]=quantizer.recover_unpred();''',1)
needle='''            std::fprintf(stderr,"HPEZCOORD q=%zu coords=%zu consumed=%zu\\n",quant_inds.size(),quant_coords.size(),quant_index);'''
repl='''            std::fprintf(stderr,"HPEZCOORD q=%zu coords=%zu ebs=%zu consumed=%zu\\n",quant_inds.size(),quant_coords.size(),quant_ebs.size(),quant_index);'''
if needle not in s:raise SystemExit('coord print missing')
s=s.replace(needle,repl,1)
needle='''                if(cf){for(size_t v:quant_coords){uint64_t u=(uint64_t)v;std::fwrite(&u,sizeof(uint64_t),1,cf);}std::fclose(cf);}\n            }'''
repl='''                if(cf){for(size_t v:quant_coords){uint64_t u=(uint64_t)v;std::fwrite(&u,sizeof(uint64_t),1,cf);}std::fclose(cf);}\n                if(quant_ebs.size()==quant_inds.size()){FILE *ef=std::fopen("hpez_final_quant_eb_f64.bin","wb");if(ef){std::fwrite(quant_ebs.data(),sizeof(double),quant_ebs.size(),ef);std::fclose(ef);}}\n            }'''
if needle not in s:raise SystemExit('coord dump missing')
s=s.replace(needle,repl,1)
p.write_text(s)
print('patched decoder EB dump')
