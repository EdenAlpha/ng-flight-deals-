from pathlib import Path
p=Path('hpez-src/include/QoZ/compressor/SZInterpolationCompressor.hpp')
s=p.read_text()
needle='''        template<uint NN = N>\n        typename std::enable_if<NN == 3, double>::type\n        block_interpolation(T *data, std::array<size_t, N> begin, std::array<size_t, N> end, const PredictorBehavior pb,\n                            const std::string &interp_func,const QoZ::Interp_Meta & meta, size_t stride = 1,int tuning=0,int cross_block=0) {//cross block: 0 or conf.num\n\n            double predict_error = 0;'''
repl='''        template<uint NN = N>\n        typename std::enable_if<NN == 3, double>::type\n        block_interpolation(T *data, std::array<size_t, N> begin, std::array<size_t, N> end, const PredictorBehavior pb,\n                            const std::string &interp_func,const QoZ::Interp_Meta & meta, size_t stride = 1,int tuning=0,int cross_block=0) {//cross block: 0 or conf.num\n\n            // Critical synchronization invariant: encoder-only tuning invocations and committed\n            // invocations must begin from the same decoder-known residual state.\n            quantizer.reset_feedback();\n            double predict_error = 0;'''
if needle not in s: raise SystemExit('3D interpolation signature not found')
s=s.replace(needle,repl,1)
p.write_text(s)
print('patched 3D invocation synchronization')
