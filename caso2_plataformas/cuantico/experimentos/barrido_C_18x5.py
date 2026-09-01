import os, sys
from collections import deque
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
)
import cuantico.formulacion.qubo_caso2_18x5 as qmod
from cuantico.solvers.simulated_annealing import resolver_qubo_sa

VALORES_C=[1.0,2.0,3.0]
NUM_READS=100
NUM_SWEEPS=1000
SEED=20260826

class Tee:
    def __init__(self,*s): self.s=s
    def write(self,d):
        for x in self.s:
            x.write(d); x.flush()
    def flush(self):
        for x in self.s: x.flush()

def bfs(grafo,inicio,meta):
    cola=deque([inicio]); ant={inicio:None}
    while cola:
        a=cola.popleft()
        if a==meta: break
        for b in grafo.get(a,[]):
            if b not in ant:
                ant[b]=a; cola.append(b)
    if meta not in ant: return None
    camino=[]; a=meta
    while a is not None:
        camino.append(a); a=ant[a]
    return list(reversed(camino))

def reconstruir_ruta(muestra):
    activas=[e for e,v in muestra.items() if int(v)==1]
    sig={}
    for o,d in activas:
        sig.setdefault(o,[]).append(d)
    ruta=[qmod.START]; actual=qmod.START; visit={actual}
    while actual!=qmod.GOAL:
        cand=sig.get(actual,[])
        if len(cand)!=1: return None
        actual=cand[0]
        if actual in visit: return None
        ruta.append(actual); visit.add(actual)
        if len(ruta)>qmod.L_OBJETIVO+2: return None
    return ruta

def delta_l(grafo,muestra):
    ruta=reconstruir_ruta(muestra)
    if ruta is None: return None
    nodos=set(ruta)
    sub={o:[d for d in grafo.get(o,[]) if d in nodos] for o in nodos}
    cbfs=bfs(sub,qmod.START,qmod.GOAL)
    if cbfs is None: return None
    return (len(ruta)-1)-(len(cbfs)-1)

def ejecutar_c(grafo,c):
    qmod.C=float(c)
    Q,offset=qmod.construir_qubo(grafo)
    ss=resolver_qubo_sa(Q,num_reads=NUM_READS,num_sweeps=NUM_SWEEPS,seed=SEED)

    regs=[]
    for datum in ss.data(fields=["sample","num_occurrences"]):
        muestra={k:int(v) for k,v in datum.sample.items()}
        ev=qmod.evaluar_restricciones(grafo,muestra)
        dl=delta_l(grafo,muestra) if ev["factible_qubo"] else None
        for _ in range(int(datum.num_occurrences)):
            regs.append((ev,dl))

    total=len(regs)
    fact=[r for r in regs if r[0]["factible_qubo"]]

    def pct(fn):
        n=sum(1 for ev,_ in regs if fn(ev))
        return n,100*n/total

    return {
        "C":c,
        "fact":len(fact),
        "fact_pct":100*len(fact)/total,
        "start":pct(lambda e:e["salida_start"]==1),
        "goal":pct(lambda e:e["entrada_goal"]==1),
        "flujo":pct(lambda e:len(e["violaciones_flujo"])==0),
        "long":pct(lambda e:e["numero_saltos"]==qmod.L_OBJETIVO),
        "sub":pct(lambda e:e["numero_subidas"]==qmod.SUBIDAS_OBJETIVO),
        "baj":pct(lambda e:e["numero_bajadas"]==qmod.BAJADAS_OBJETIVO),
        "sin_atajo":sum(1 for ev,dl in fact if dl==0),
        "con_atajo":sum(1 for ev,dl in fact if dl is not None and dl>0),
    }

def ejecutar():
    cand=obtener_anclas_candidatas(qmod.ANCHO,qmod.ALTO,qmod.START,qmod.GOAL)
    posiciones=[qmod.START]+cand+[qmod.GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,qmod.START,qmod.GOAL)

    print("="*96)
    print("CASO 2 — BARRIDO C EN INSTANCIA 18x5")
    print("="*96)
    print(f"C probados: {VALORES_C}")
    print(f"reads={NUM_READS}, sweeps={NUM_SWEEPS}, seed={SEED}")
    print()

    resultados=[]
    for c in VALORES_C:
        r=ejecutar_c(grafo,c)
        resultados.append(r)
        print(f"C={c}")
        print(f"  Factibilidad total: {r['fact']}/{NUM_READS} ({r['fact_pct']:.2f}%)")
        print(f"  START: {r['start'][1]:.2f}%")
        print(f"  GOAL: {r['goal'][1]:.2f}%")
        print(f"  Flujo: {r['flujo'][1]:.2f}%")
        print(f"  Longitud: {r['long'][1]:.2f}%")
        print(f"  Subidas: {r['sub'][1]:.2f}%")
        print(f"  Bajadas: {r['baj'][1]:.2f}%")
        print(f"  Factibles sin atajo: {r['sin_atajo']}")
        print(f"  Factibles con atajo: {r['con_atajo']}")
        print()

    print("RESUMEN")
    print("C | Fact.% | Flujo | Long. | Sub. | Baj. | sin atajo | con atajo")
    print("-"*72)
    for r in resultados:
        print(
            f"{r['C']:.1f} | {r['fact_pct']:.2f} | {r['flujo'][1]:.2f} | "
            f"{r['long'][1]:.2f} | {r['sub'][1]:.2f} | {r['baj'][1]:.2f} | "
            f"{r['sin_atajo']} | {r['con_atajo']}"
        )

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"barrido_C_18x5_{marca}.txt")
    original=sys.stdout
    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original
    print(f"\nTXT generado correctamente: {ruta}")