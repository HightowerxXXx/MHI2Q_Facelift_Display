"""LZO1X decompress with provenance: for each output byte, source index if literal else -1."""
def decomp_prov(src):
    ip=0; out=bytearray(); prov=[]; state=0
    def lit(n):
        nonlocal ip
        for k in range(n): out.append(src[ip]); prov.append(ip); ip+=1
    def match(m,n):
        for k in range(n): out.append(out[m+k]); prov.append(-1)
    if src[0]>17:
        t=src[0]-17; ip=1; lit(t); state = t if t<4 else 4
    while True:
        t=src[ip]; ip+=1
        if t<16:
            if state==0:
                if t==0:
                    while src[ip]==0: t+=255; ip+=1
                    t+=15+src[ip]; ip+=1
                lit(t+3); state=4; continue
            elif state!=4:
                nx=t&3; m=len(out)-1-(t>>2)-(src[ip]<<2); ip+=1; L=2
            else:
                nx=t&3; m=len(out)-0x801-(t>>2)-(src[ip]<<2); ip+=1; L=3
        elif t>=64:
            nx=t&3; m=len(out)-1-((t>>2)&7)-(src[ip]<<3); ip+=1; L=(t>>5)+1
        elif t>=32:
            L=t&31
            if L==0:
                while src[ip]==0: L+=255; ip+=1
                L+=31+src[ip]; ip+=1
            L+=2; v=src[ip]|(src[ip+1]<<8); ip+=2; m=len(out)-1-(v>>2); nx=v&3
        else:
            m=len(out)-((t&8)<<11); L=t&7
            if L==0:
                while src[ip]==0: L+=255; ip+=1
                L+=7+src[ip]; ip+=1
            L+=2; v=src[ip]|(src[ip+1]<<8); ip+=2; m-=v>>2; nx=v&3
            if m==len(out): return bytes(out),prov
            m-=0x4000
        match(m,L); state=nx; lit(nx)
