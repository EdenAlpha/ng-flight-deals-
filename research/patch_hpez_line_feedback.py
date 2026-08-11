from pathlib import Path
q=Path('hpez-src/include/QoZ/quantizer/IntegerQuantizer.hpp')
s=q.read_text()
s=s.replace('namespace QoZ {', '#ifndef HPEZ_RESIDUAL_ALPHA\n#define HPEZ_RESIDUAL_ALPHA 0.0\n#endif\n\nnamespace QoZ {',1)
# Both overwrite encoders use a decoder-known shifted lattice.
s=s.replace('int quantize_and_overwrite(T &data, T pred,bool save_unpred=true) {\n\n            \n            T diff = data - pred;', 'int quantize_and_overwrite(T &data, T pred,bool save_unpred=true) {\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T diff = data - pred;',1)
s=s.replace('int quantize_and_overwrite(T ori, T pred, T &dest,bool save_unpred=true) {\n\n            \n            T diff = ori - pred;', 'int quantize_and_overwrite(T ori, T pred, T &dest,bool save_unpred=true) {\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T diff = ori - pred;',1)
# Encoder success updates state to reconstructed residual relative to the unshifted predictor.
s=s.replace('data = decompressed_data;\n                    return quant_index_shifted;', 'data = decompressed_data;\n                    feedback = (double)(decompressed_data - raw_pred);\n                    return quant_index_shifted;',1)
s=s.replace('dest = decompressed_data;\n                    return quant_index_shifted;', 'dest = decompressed_data;\n                    feedback = (double)(decompressed_data - raw_pred);\n                    return quant_index_shifted;',1)
# Reset state only on unpredictable overwrite paths. Be surgical, not global.
s=s.replace('''if (fabs(decompressed_data - data) > this->error_bound) {\n                    if(save_unpred)\n                        unpred.push_back(data);\n                    return 0;''','''if (fabs(decompressed_data - data) > this->error_bound) {\n                    if(save_unpred) unpred.push_back(data);\n                    feedback = 0.0;\n                    return 0;''',1)
s=s.replace('''} else {\n                if(save_unpred)\n                    unpred.push_back(data);\n                return 0;\n            }\n        }\n\n        int quantize_and_overwrite(T ori''','''} else {\n                if(save_unpred) unpred.push_back(data);\n                feedback = 0.0;\n                return 0;\n            }\n        }\n\n        int quantize_and_overwrite(T ori''',1)
s=s.replace('''if (fabs(decompressed_data - ori) > this->error_bound) {\n                    if(save_unpred)\n                        unpred.push_back(ori);\n                    dest = ori;\n                    return 0;''','''if (fabs(decompressed_data - ori) > this->error_bound) {\n                    if(save_unpred) unpred.push_back(ori);\n                    dest = ori; feedback = 0.0;\n                    return 0;''',1)
s=s.replace('''} else {\n                if(save_unpred)\n                    unpred.push_back(ori);\n                dest = ori;\n                return 0;\n            }\n        }''','''} else {\n                if(save_unpred) unpred.push_back(ori);\n                dest = ori; feedback = 0.0;\n                return 0;\n            }\n        }''',1)
old='''        T recover(T pred, int quant_index) {\n\n            \n            if (quant_index) {\n                return recover_pred(pred, quant_index);\n            } else {\n                return recover_unpred();\n            }\n        }'''
new='''        T recover(T pred, int quant_index) {\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T out;\n            if (quant_index) {\n                out = recover_pred(pred, quant_index);\n                feedback = (double)(out - raw_pred);\n            } else {\n                out = recover_unpred();\n                feedback = 0.0;\n            }\n            return out;\n        }'''
if old not in s: raise SystemExit('recover block not found')
s=s.replace(old,new,1)
s=s.replace('void clear() {\n            unpred.clear();\n            index = 0;\n        }', 'void clear() { unpred.clear(); index = 0; feedback = 0.0; }\n\n        void reset_feedback() { feedback = 0.0; }',1)
s=s.replace('virtual void precompress_data() {};', 'virtual void precompress_data() { feedback = 0.0; };',1)
s=s.replace('virtual void predecompress_data() {};', 'virtual void predecompress_data() { feedback = 0.0; };',1)
s=s.replace('double error_bound;\n        double error_bound_reciprocal;', 'double feedback = 0.0;\n        double error_bound;\n        double error_bound_reciprocal;',1)
q.write_text(s)

# Scope memory to one physical interpolation line. This call is hit identically in encode/decode.
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
t=p.read_text()
needle='''        double block_interpolation_1d(T *data, size_t begin, size_t end, size_t stride,const std::string &interp_func,const PredictorBehavior pb,const QoZ::Interp_Meta &meta,int tuning=0) {\n            size_t n = (end - begin) / stride + 1;'''
repl='''        double block_interpolation_1d(T *data, size_t begin, size_t end, size_t stride,const std::string &interp_func,const PredictorBehavior pb,const QoZ::Interp_Meta &meta,int tuning=0) {\n            quantizer.reset_feedback();\n            size_t n = (end - begin) / stride + 1;'''
if needle not in t: raise SystemExit('1d block signature not found')
t=t.replace(needle,repl,1)
p.write_text(t)
print('patched line-scoped feedback')
