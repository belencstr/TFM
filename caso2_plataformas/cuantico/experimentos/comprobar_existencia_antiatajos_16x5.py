import os, sys
from datetime import datetime
from ortools.sat.python import cp_model

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import ANCHO_PLATAFORMA, obtener_anclas_candidatas, construir_grafo_segmentos_v4, contar_aristas

ANCHO=16
ALTO=5
START=(0,2)
GOAL=(15,2)
L_OBJETIVO=5
SUBIDAS_OBJETIVO=2
BAJADAS_OBJETIVO=2
MAX_TIEMPO=60.0
SEED=20260827

def se_solapan(a,b):
    if a[1]!=b[1]:
        return False
    a_fin=a[0]+ANCHO_PLATAFORMA-1
    b_fin=b[0]+ANCHO_PLATAFORMA-1
    return not (a_fin < b[0] or b_fin < a[0])

def resolver(grafo):
    model=cp_model.CpModel()
    nodos=list(grafo.keys())
    usado={n:model.NewBoolVar(f"u_{n[0]}_{n[1]}") for n in nodos}
    model.Add(usado[START]==1)
    model.Add(usado[GOAL]==1)

    z={}
    entradas={n:[] for n in nodos}
    salidas={n:[] for n in nodos}
    for o,ds in grafo.items():
        for d in ds:
            var=model.NewBoolVar(f"z_{o[0]}_{o[1]}__{d[0]}_{d[1]}")
            z[(o,d)]=var
            salidas[o].append(var)
            entradas[d].append(var)

    model.Add(sum(salidas[START])==1)
    if entradas[START]:
        model.Add(sum(entradas[START])==0)
    model.Add(sum(entradas[GOAL])==1)
    if salidas[GOAL]:
        model.Add(sum(salidas[GOAL])==0)

    for n in nodos:
        if n in (START,GOAL):
            continue
        ent=sum(entradas[n]); sal=sum(salidas[n])
        model.Add(ent==sal)
        model.Add(ent<=1); model.Add(sal<=1)
        model.Add(usado[n]==ent)

    candidatas=[n for n in nodos if n not in (START,GOAL)]
    for i in range(len(candidatas)):
        for j in range(i+1,len(candidatas)):
            a,b=candidatas[i],candidatas[j]
            if se_solapan(a,b):
                model.Add(usado[a]+usado[b] <= 1)

    model.Add(sum(z.values())==L_OBJETIVO)

    subidas=[]; bajadas=[]
    for (o,d),var in z.items():
        dy=d[1]-o[1]
        if dy>0: subidas.append(var)
        elif dy<0: bajadas.append(var)

    model.Add(sum(subidas)==SUBIDAS_OBJETIVO)
    model.Add(sum(bajadas)==BAJADAS_OBJETIVO)

    for (o,d),var in z.items():
        model.Add(usado[o]+usado[d] <= 1 + var)

    solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=MAX_TIEMPO
    solver.parameters.random_seed=SEED
    solver.parameters.num_search_workers=8
    status=solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status":solver.StatusName(status),"ruta":None,"tiempo":solver.WallTime()}

    saltos=[(o,d) for (o,d),var in z.items() if solver.Value(var)==1]
    siguiente={o:d for o,d in saltos}
    ruta=[START]
    actual=START
    while actual!=GOAL:
        if actual not in siguiente:
            return {"status":solver.StatusName(status),"ruta":None,"tiempo":solver.WallTime()}
        actual=siguiente[actual]
        ruta.append(actual)
    return {"status":solver.StatusName(status),"ruta":ruta,"tiempo":solver.WallTime()}

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)
    r=resolver(grafo)

    print("="*88)
    print("CASO 2 — EXISTENCIA DE SOLUCION 16x5 CON ANTIATAJOS")
    print("="*88)
    print(f"Mapa: {ANCHO} x {ALTO}")
    print(f"Variables/aristas potenciales: {contar_aristas(grafo)}")
    print(f"L objetivo: {L_OBJETIVO}")
    print(f"Subidas exactas: {SUBIDAS_OBJETIVO}")
    print(f"Bajadas exactas: {BAJADAS_OBJETIVO}")
    print()
    print(f"Estado CP-SAT: {r['status']}")
    print(f"Tiempo: {r['tiempo']:.4f} s")
    if r["ruta"] is None:
        print("Existe solucion sin atajos: NO")
    else:
        print("Existe solucion sin atajos: SI")
        print("Ruta:")
        print(" -> ".join(str(p) for p in r["ruta"]))

def main():
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"existencia_antiatajos_16x5_{marca}.txt")
    original=sys.stdout
    class Tee:
        def __init__(self,*s): self.s=s
        def write(self,d):
            for x in self.s: x.write(d); x.flush()
        def flush(self):
            for x in self.s: x.flush()
    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original
    print(f"\nTXT generado correctamente: {ruta}")

if __name__=="__main__":
    main()