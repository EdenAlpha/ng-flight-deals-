import struct,sys
import numpy as np
import imperial_channel_transfer_generator as g

def model_frame_fixed(co):
    raw=np.asarray(co,dtype='<f4').tobytes()
    buf=b'CTG1'+struct.pack('<H',len(co))+raw
    if buf[:4]!=b'CTG1':
        raise RuntimeError('frame')
    n=struct.unpack_from('<H',buf,4)[0]
    cod=np.frombuffer(buf[6:6+4*n],dtype='<f4').copy()
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):
        raise RuntimeError('model replay')
    return buf,cod

g.model_frame=model_frame_fixed
if __name__=='__main__':g.main(sys.argv[1])
