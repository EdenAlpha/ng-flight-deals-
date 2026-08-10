import io,tarfile

def parse(data):
    try:
        out=[]
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as tf:
            for m in tf.getmembers():
                if not m.isfile() or m.size<0:continue
                ds=int(m.offset_data);sz=int(m.size)
                if ds<0 or ds+sz>len(data):return None
                out.append((ds,sz,m.name.encode('utf-8','surrogateescape')))
        return out
    except Exception:return None
