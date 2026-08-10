#!/usr/bin/env python3
import os,sys,tempfile,subprocess,zipfile
HERE=os.path.dirname(os.path.abspath(__file__))
AX=os.path.join(HERE,'axiom_beast.py')

def rt(name,data):
    td=tempfile.mkdtemp();src=os.path.join(td,name);arc=src+'.axb';out=src+'.out'
    open(src,'wb').write(data)
    subprocess.run([sys.executable,AX,'c',src,arc,'--effort','fast'],check=True)
    subprocess.run([sys.executable,AX,'d',arc,out],check=True)
    assert open(out,'rb').read()==data
    return len(data),os.path.getsize(arc)

print('text',rt('x.txt',(b'alpha beta gamma alpha beta\n'*1000)))
print('csv',rt('x.csv',b'date,entity,value\n'+b''.join(f'2026-01-{(i%28)+1:02d},e{i%7},{i//7}\n'.encode() for i in range(3000))))
with tempfile.TemporaryDirectory() as td:
    z=os.path.join(td,'x.zip')
    with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as f:
        f.writestr('a.txt',b'law graph '*5000)
    d=open(z,'rb').read();print('zip',rt('x.zip',d))
print('OK')
