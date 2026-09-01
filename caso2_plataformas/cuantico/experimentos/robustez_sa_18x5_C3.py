import os, sys
from collections import deque
from datetime import datetime
from statistics import mean, pstdev

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
)

import cuantico.formulacion.qubo_caso2_18x5 as qmod
from cuantico.solvers.simulated_annealing import resolver_qubo_sa

# Configuración final provisional
qmod.C = 3.0

NUM_READS=100
NUM_SWEEPS=1000
SEMILLAS=[
    20260801, 20260802, 20260803, 20260804, 20260805,
    20260806, 20260807, 20260808, 20260809, 20260810,
    20260811, 20260812, 20260813, 20260814, 20260815,
    20260816, 20260817, 20260818, 20260819, 20260820,
]

class Tee:
    def __init__(self,*s): self.s=s
    def write(self,d):
        for x in self.s:
            x.write(d); x.flush()
    def flush(self):
        for x in self.s: x.flush()

def bfs(grafo,inicio,meta):
    cola=deque([inicio])
    ant={inicio:None}
    while cola:
        a=cola.popleft()
        if a==meta:
            break
        for b in grafo.get(a,[]):
            if b not in ant:
                ant[b]=a
                cola.append(b)
    if meta not in ant:
        return None
    camino=[]
    a=meta
    while a is not None:
        camino.append(a)
        a=ant[a]
    return list(reversed(camino))

def reconstruir_ruta(muestra):
    activas=[e for e,v in muestra.items() if int(v)==1]
    sig={}
    for o,d in activas:
        sig.setdefault(o,[]).append(d)

    ruta=[qmod.START]
    actual=qmod.START
    visit={actual}

    while actual!=qmod.GOAL:
        cand=sig.get(actual,[])
        if len(cand)!=1:
            return None
        actual=cand[0]
        if actual in visit:
            return None
        ruta.append(actual)
        visit.add(actual)
        if len(ruta)>qmod.L_OBJETIVO+2:
            return None

    return ruta

def delta_l(grafo,muestra):
    ruta=reconstruir_ruta(muestra)
    if ruta is None:
        return None

    nodos=set(ruta)
    sub={
        o:[d for d in grafo.get(o,[]) if d in nodos]
        for o in nodos
    }

    cbfs=bfs(sub,qmod.START,qmod.GOAL)
    if cbfs is None:
        return None

    return (len(ruta)-1)-(len(cbfs)-1)

def ejecutar_semilla(grafo,Q,offset,seed):
    ss=resolver_qubo_sa(
        Q,
        num_reads=NUM_READS,
        num_sweeps=NUM_SWEEPS,
        seed=seed,
    )

    registros=[]

    for datum in ss.data(fields=["sample","num_occurrences"]):
        muestra={k:int(v) for k,v in datum.sample.items()}
        ev=qmod.evaluar_restricciones(grafo,muestra)
        energia=qmod.energia_qubo(Q,offset,muestra)
        dl=delta_l(grafo,muestra) if ev["factible_qubo"] else None

        for _ in range(int(datum.num_occurrences)):
            registros.append((energia,ev,dl))

    factibles=[r for r in registros if r[1]["factible_qubo"]]
    sin_atajo=sum(1 for _,_,dl in factibles if dl==0)
    con_atajo=sum(1 for _,_,dl in factibles if dl is not None and dl>0)

    return {
        "seed":seed,
        "energia_min":min(r[0] for r in registros),
        "factibles":len(factibles),
        "fact_pct":100*len(factibles)/len(registros),
        "sin_atajo":sin_atajo,
        "con_atajo":con_atajo,
        "sin_atajo_pct_sobre_factibles":(
            100*sin_atajo/len(factibles) if factibles else 0.0
        ),
    }

def ejecutar():
    candidatas=obtener_anclas_candidatas(
        qmod.ANCHO,qmod.ALTO,qmod.START,qmod.GOAL
    )
    posiciones=[qmod.START]+candidatas+[qmod.GOAL]
    grafo=construir_grafo_segmentos_v4(
        posiciones,qmod.START,qmod.GOAL
    )

    Q,offset=qmod.construir_qubo(grafo)

    print("="*100)
    print("CASO 2 — ROBUSTEZ SIMULATED ANNEALING")
    print("="*100)
    print(f"Mapa: {qmod.ANCHO} x {qmod.ALTO}")
    print(f"C = {qmod.C}")
    print(f"reads por semilla = {NUM_READS}")
    print(f"sweeps = {NUM_SWEEPS}")
    print(f"numero de semillas = {len(SEMILLAS)}")
    print()

    resultados=[]

    for seed in SEMILLAS:
        r=ejecutar_semilla(grafo,Q,offset,seed)
        resultados.append(r)
        print(
            f"seed={seed} | "
            f"Emin={r['energia_min']:.1f} | "
            f"fact={r['factibles']}/{NUM_READS} "
            f"({r['fact_pct']:.1f}%) | "
            f"sin atajo={r['sin_atajo']} | "
            f"con atajo={r['con_atajo']}"
        )

    fact_pcts=[r["fact_pct"] for r in resultados]
    sin_atajo_counts=[r["sin_atajo"] for r in resultados]
    sin_atajo_pct=[r["sin_atajo_pct_sobre_factibles"] for r in resultados]

    total_fact=sum(r["factibles"] for r in resultados)
    total_sin=sum(r["sin_atajo"] for r in resultados)
    total_con=sum(r["con_atajo"] for r in resultados)

    print()
    print("="*100)
    print("RESUMEN")
    print("="*100)
    print(f"Lecturas totales: {len(SEMILLAS)*NUM_READS}")
    print(f"Factibles totales: {total_fact}")
    print(f"Factibilidad global: {100*total_fact/(len(SEMILLAS)*NUM_READS):.2f}%")
    print(f"Factibilidad media por semilla: {mean(fact_pcts):.2f}%")
    print(f"Desviacion tipica factibilidad: {pstdev(fact_pcts):.2f}")
    print(f"Min factibilidad por semilla: {min(fact_pcts):.2f}%")
    print(f"Max factibilidad por semilla: {max(fact_pcts):.2f}%")
    print()
    print(f"Factibles sin atajo totales: {total_sin}")
    print(f"Factibles con atajo totales: {total_con}")
    if total_fact:
        print(f"Sin atajo sobre factibles: {100*total_sin/total_fact:.2f}%")
        print(f"Con atajo sobre factibles: {100*total_con/total_fact:.2f}%")
    print()
    print(f"Media sin atajo por semilla: {mean(sin_atajo_counts):.2f}")
    print(f"Media % sin atajo sobre factibles por semilla: {mean(sin_atajo_pct):.2f}%")

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)

    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(
        carpeta,
        f"robustez_sa_18x5_C3_{len(SEMILLAS)}seeds_{marca}.txt"
    )

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