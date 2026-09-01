from collections import defaultdict

ANCHO=16
ALTO=5
START=(0,2)
GOAL=(15,2)
L_OBJETIVO=5
SUBIDAS_OBJETIVO=2
BAJADAS_OBJETIVO=2
A=B=C=D=E=F=1.0

def _orden(v):
    o,d=v
    return (o[0],o[1],d[0],d[1])

def _add_lin(Q,v,c):
    Q[(v,v)] += float(c)

def _add_quad(Q,v1,v2,c):
    if v1==v2:
        _add_lin(Q,v1,c); return
    key=(v1,v2) if _orden(v1)<=_orden(v2) else (v2,v1)
    Q[key]+=float(c)

def add_square(Q,offset,coef,const,peso):
    offset += peso*const*const
    items=list(coef.items())
    for v,a in items:
        _add_lin(Q,v,peso*(a*a+2*const*a))
    for i in range(len(items)):
        vi,ai=items[i]
        for j in range(i+1,len(items)):
            vj,aj=items[j]
            _add_quad(Q,vi,vj,peso*2*ai*aj)
    return offset

def construir_qubo(grafo):
    Q=defaultdict(float); offset=0.0
    aristas=[(o,d) for o,ds in grafo.items() for d in ds]
    entradas={n:[] for n in grafo}; salidas={n:[] for n in grafo}
    for e in aristas:
        o,d=e; salidas[o].append(e); entradas[d].append(e)

    offset=add_square(Q,offset,{e:1 for e in salidas[START]},-1,A)
    offset=add_square(Q,offset,{e:1 for e in entradas[GOAL]},-1,B)

    for n in grafo:
        if n in (START,GOAL): continue
        coef={}
        for e in entradas[n]: coef[e]=coef.get(e,0)+1
        for e in salidas[n]: coef[e]=coef.get(e,0)-1
        if coef:
            offset=add_square(Q,offset,coef,0,C)

    offset=add_square(Q,offset,{e:1 for e in aristas},-L_OBJETIVO,D)

    subidas=[e for e in aristas if e[1][1]>e[0][1]]
    bajadas=[e for e in aristas if e[1][1]<e[0][1]]
    offset=add_square(Q,offset,{e:1 for e in subidas},-SUBIDAS_OBJETIVO,E)
    offset=add_square(Q,offset,{e:1 for e in bajadas},-BAJADAS_OBJETIVO,F)

    Q={k:v for k,v in Q.items() if abs(v)>1e-12}
    return Q,offset

def muestra_desde_ruta(grafo,ruta):
    aristas=[(o,d) for o,ds in grafo.items() for d in ds]
    muestra={e:0 for e in aristas}
    for o,d in zip(ruta[:-1],ruta[1:]):
        e=(o,d)
        if e not in muestra:
            raise ValueError(f"La arista {e} no existe en el grafo.")
        muestra[e]=1
    return muestra

def energia_qubo(Q,offset,muestra):
    E=offset
    for (v1,v2),c in Q.items():
        E += c*muestra.get(v1,0)*muestra.get(v2,0)
    return E

def evaluar_restricciones(grafo,muestra):
    activas=[e for e,v in muestra.items() if int(v)==1]
    entradas={n:0 for n in grafo}; salidas={n:0 for n in grafo}
    for o,d in activas:
        salidas[o]+=1; entradas[d]+=1

    p_inicio=A*(salidas[START]-1)**2
    p_meta=B*(entradas[GOAL]-1)**2
    p_flujo=0.0; viol=[]
    for n in grafo:
        if n in (START,GOAL): continue
        dif=entradas[n]-salidas[n]
        if dif!=0: viol.append((n,entradas[n],salidas[n]))
        p_flujo += C*dif*dif

    ns=len(activas)
    nup=sum(1 for o,d in activas if d[1]>o[1])
    ndown=sum(1 for o,d in activas if d[1]<o[1])
    nflat=sum(1 for o,d in activas if d[1]==o[1])

    p_long=D*(ns-L_OBJETIVO)**2
    p_up=E*(nup-SUBIDAS_OBJETIVO)**2
    p_down=F*(ndown-BAJADAS_OBJETIVO)**2
    total=p_inicio+p_meta+p_flujo+p_long+p_up+p_down

    return {
        "salida_start":salidas[START],
        "entrada_goal":entradas[GOAL],
        "numero_saltos":ns,
        "numero_subidas":nup,
        "numero_bajadas":ndown,
        "numero_planos":nflat,
        "violaciones_flujo":viol,
        "penalizacion_inicio":p_inicio,
        "penalizacion_meta":p_meta,
        "penalizacion_flujo":p_flujo,
        "penalizacion_longitud":p_long,
        "penalizacion_subidas":p_up,
        "penalizacion_bajadas":p_down,
        "energia_componentes":total,
        "factible_qubo":abs(total)<1e-12,
    }   