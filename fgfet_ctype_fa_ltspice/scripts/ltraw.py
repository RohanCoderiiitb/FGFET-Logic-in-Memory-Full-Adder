import struct, numpy as np
def read_raw(fn):
    b=open(fn,'rb').read()
    i=b.find('Binary:\n'.encode('utf-16le'))
    hdr=b[:i].decode('utf-16le'); data=b[i+len('Binary:\n')*2:]
    L=hdr.splitlines()
    nv=int([l for l in L if l.startswith('No. Variables')][0].split(':')[1])
    npnt=int([l for l in L if l.startswith('No. Points')][0].split(':')[1])
    flags=[l for l in L if l.startswith('Flags')][0]
    k=L.index('Variables:')
    names=[L[k+1+j].split()[1] for j in range(nv)]
    dbl='double' in flags
    out=np.zeros((npnt,nv))
    if dbl:
        arr=np.frombuffer(data,dtype=np.float64,count=npnt*nv).reshape(npnt,nv); out=arr.copy()
    else:
        dt=np.dtype([('t','<f8')]+[('v%d'%j,'<f4') for j in range(nv-1)])
        arr=np.frombuffer(data,dtype=dt,count=npnt)
        out[:,0]=arr['t']
        for j in range(nv-1): out[:,j+1]=arr['v%d'%j]
    return {n.lower():out[:,j] for j,n in enumerate(names)}
