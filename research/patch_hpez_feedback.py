from pathlib import Path
p=Path('hpez-src/include/QoZ/quantizer/IntegerQuantizer.hpp')
s=p.read_text()
s=s.replace('namespace QoZ {', '#ifndef HPEZ_RESIDUAL_ALPHA\n#define HPEZ_RESIDUAL_ALPHA 0.0\n#endif\n\nnamespace QoZ {',1)
s=s.replace('int quantize_and_overwrite(T &data, T pred,bool save_unpred=true) {\n\n            \n            T diff = data - pred;', 'int quantize_and_overwrite(T &data, T pred,bool save_unpred=true) {\n\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T diff = data - pred;',1)
s=s.replace('int quantize_and_overwrite(T ori, T pred, T &dest,bool save_unpred=true) {\n\n            \n            T diff = ori - pred;', 'int quantize_and_overwrite(T ori, T pred, T &dest,bool save_unpred=true) {\n\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T diff = ori - pred;',1)
s=s.replace('data = decompressed_data;\n                    return quant_index_shifted;', 'data = decompressed_data;\n                    feedback = (double)(decompressed_data - raw_pred);\n                    return quant_index_shifted;',1)
s=s.replace('dest = decompressed_data;\n                    return quant_index_shifted;', 'dest = decompressed_data;\n                    feedback = (double)(decompressed_data - raw_pred);\n                    return quant_index_shifted;',1)
old='''        T recover(T pred, int quant_index) {\n\n            \n            if (quant_index) {\n                return recover_pred(pred, quant_index);\n            } else {\n                return recover_unpred();\n            }\n        }'''
new='''        T recover(T pred, int quant_index) {\n            T raw_pred = pred;\n            pred = pred + (T)(HPEZ_RESIDUAL_ALPHA * feedback);\n            T out;\n            if (quant_index) {\n                out = recover_pred(pred, quant_index);\n                feedback = (double)(out - raw_pred);\n            } else {\n                out = recover_unpred();\n                feedback = 0.0;\n            }\n            return out;\n        }'''
if old not in s: raise SystemExit('recover block not found')
s=s.replace(old,new,1)
# On unpredictable samples reset the synchronized state at encoder too.
s=s.replace('return 0;', 'feedback = 0.0; return 0;')
# The replacement above also touches the stateless quantize() path; that only resets state and does not change its returned index.
s=s.replace('void clear() {\n            unpred.clear();\n            index = 0;\n        }', 'void clear() {\n            unpred.clear();\n            index = 0;\n            feedback = 0.0;\n        }',1)
s=s.replace('virtual void precompress_data() {};', 'virtual void precompress_data() { feedback = 0.0; };',1)
s=s.replace('virtual void predecompress_data() {};', 'virtual void predecompress_data() { feedback = 0.0; };',1)
s=s.replace('double error_bound;\n        double error_bound_reciprocal;', 'double feedback = 0.0;\n        double error_bound;\n        double error_bound_reciprocal;',1)
p.write_text(s)
print('patched',p)
