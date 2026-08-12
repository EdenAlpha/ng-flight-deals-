from pathlib import Path

p = Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s = p.read_text()

# Dump final quantization indices and the Huffman-independent prefix.
needle = '''            quantizer.save(buffer_pos);\n            quantizer.postcompress_data();\n            quantizer.clear();\n            encoder.save(buffer_pos);\n            encoder.encode(quant_inds, buffer_pos);'''
repl = '''            quantizer.save(buffer_pos);\n            quantizer.postcompress_data();\n            quantizer.clear();\n            if(quant_inds.size() > 1000000){\n                FILE *pf=std::fopen("hpez_prefix.bin","wb");\n                if(pf){std::fwrite(buffer,1,(size_t)(buffer_pos-buffer),pf);std::fclose(pf);}\n                FILE *qf=std::fopen("hpez_final_quant_inds.bin","wb");\n                if(qf){std::fwrite(quant_inds.data(),sizeof(int),quant_inds.size(),qf);std::fclose(qf);}\n            }\n            encoder.save(buffer_pos);\n            encoder.encode(quant_inds, buffer_pos);'''
if needle not in s:
    raise SystemExit('encoder/prefix needle missing')
s = s.replace(needle, repl, 1)

# Decoder-authoritative mapping from quantization-stream order to physical sample index.
s = s.replace(
    '''        std::vector<int> quant_inds;\n        std::vector<bool> mark;''',
    '''        std::vector<int> quant_inds;\n        std::vector<size_t> quant_coords;\n        std::vector<bool> mark;''',
    1,
)
s = s.replace(
    '''            init();   \n          \n            //QoZ::Timer timer(true);''',
    '''            init();\n            quant_coords.clear(); quant_coords.reserve(num_elements);\n          \n            //QoZ::Timer timer(true);''',
    1,
)
s = s.replace(
    '''            if(!anchor){\n                *decData = quantizer.recover(0, quant_inds[quant_index++]);''',
    '''            if(!anchor){\n                quant_coords.push_back(0);\n                *decData = quantizer.recover(0, quant_inds[quant_index++]);''',
    1,
)
s = s.replace(
    '''        inline void recover(size_t idx, T &d, T pred) {\n            d = quantizer.recover(pred, quant_inds[quant_index++]);''',
    '''        inline void recover(size_t idx, T &d, T pred) {\n            quant_coords.push_back(idx);\n            d = quantizer.recover(pred, quant_inds[quant_index++]);''',
    1,
)
s = s.replace(
    '''            if(mode==-1){//recover\n                d = quantizer.recover(pred, quant_inds[quant_index++]);''',
    '''            if(mode==-1){//recover\n                quant_coords.push_back(idx);\n                d = quantizer.recover(pred, quant_inds[quant_index++]);''',
    1,
)

# Anchor-grid coordinates, if the selected HPEZ configuration uses anchors.
s = s.replace(
    '''                for (size_t x=0;x<global_dimensions[0];x+=maxStep){\n                    decData[x]=quantizer.recover_unpred();''',
    '''                for (size_t x=0;x<global_dimensions[0];x+=maxStep){\n                    quant_coords.push_back(x);\n                    decData[x]=quantizer.recover_unpred();''',
    1,
)
s = s.replace(
    '''                    for (size_t y=0;y<global_dimensions[1];y+=maxStep){\n                        decData[x*dimension_offsets[0]+y]=quantizer.recover_unpred();''',
    '''                    for (size_t y=0;y<global_dimensions[1];y+=maxStep){\n                        quant_coords.push_back(x*dimension_offsets[0]+y);\n                        decData[x*dimension_offsets[0]+y]=quantizer.recover_unpred();''',
    1,
)
s = s.replace(
    '''                        for(size_t z=0;z<global_dimensions[2];z+=anchor_strides[2]){\n                            decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z]=quantizer.recover_unpred();''',
    '''                        for(size_t z=0;z<global_dimensions[2];z+=anchor_strides[2]){\n                            quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z);\n                            decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z]=quantizer.recover_unpred();''',
    1,
)
s = s.replace(
    '''                            for(size_t w=0;w<global_dimensions[3];w+=anchor_strides[3]){\n                                decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w]=quantizer.recover_unpred();''',
    '''                            for(size_t w=0;w<global_dimensions[3];w+=anchor_strides[3]){\n                                quant_coords.push_back(x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w);\n                                decData[x*dimension_offsets[0]+y*dimension_offsets[1]+z*dimension_offsets[2]+w]=quantizer.recover_unpred();''',
    1,
)

needle_end = '''            quantizer.postdecompress_data();\n            return decData;'''
repl_end = '''            std::fprintf(stderr,"HPEZCOORD q=%zu coords=%zu consumed=%zu\\n",quant_inds.size(),quant_coords.size(),quant_index);\n            if(quant_coords.size()==quant_inds.size() && quant_index==quant_inds.size()){\n                FILE *cf=std::fopen("hpez_final_quant_coords_u64.bin","wb");\n                if(cf){for(size_t v:quant_coords){uint64_t u=(uint64_t)v;std::fwrite(&u,sizeof(uint64_t),1,cf);}std::fclose(cf);}\n            }\n            quantizer.postdecompress_data();\n            return decData;'''
if needle_end not in s:
    raise SystemExit('decoder dump needle missing')
s = s.replace(needle_end, repl_end, 1)

p.write_text(s)
print('patched HPEZ quant stream, prefix, and decoder coordinate dump')
