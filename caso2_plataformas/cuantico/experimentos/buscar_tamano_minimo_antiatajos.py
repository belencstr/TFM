import os, sys
from datetime import datetime
from ortools.sat.python import cp_model

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA,
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
    contar_aristas,
)

ALTO=5
L_OBJETIVO=5
SUBIDAS_OBJETIVO=2
BAJADAS_OBJETIVO=2
MAX_TIEMPO=60.0
SEED=20260827

TAMANOS=[18,20]

def se_solapan(a,b):
    if a[1]!=b[1]:
        return False
    a_fin=a[0]+ANCHO_PLATAFORMA-1
    b_fin=b[0]+ANCHO_PLATAFORMA-1
    return not (a_fin < b[0] or b_fin < a[0])

def resolver(ancho):
    start=(0,2)
    goal=(ancho-1,2)

    candidatas=obtener_anclas_candidatas(ancho,ALTO,start,goal)
    posiciones=[start]+candidatas+[goal]
    grafo=construir_grafo_segmentos_v4(posiciones,start,goal)

    model=cp_model.CpModel()
    nodos=list(grafo.keys())

    usado={n:model.NewBoolVar(f"u_{n[0]}_{n[1]}") for n in nodos}
    model.Add(usado[start]==1)
    model.Add(usado[goal]==1)

    z={}
    entradas={n:[] for n in nodos}
    salidas={n:[] for n in nodos}

    for o,ds in grafo.items():
        for d in ds:
            var=model.NewBoolVar(f"z_{o[0]}_{o[1]}__{d[0]}_{d[1]}")
            z[(o,d)]=var
            salidas[o].append(var)
            entradas[d].append(var)

    model.Add(sum(salidas[start])==1)
    if entradas[start]:
        model.Add(sum(entradas[start])==0)

    model.Add(sum(entradas[goal])==1)
    if salidas[goal]:
        model.Add(sum(salidas[goal])==0)

    for n in nodos:
        if n in (start,goal):
            continue
        ent=sum(entradas[n])
        sal=sum(salidas[n])
        model.Add(ent==sal)
        model.Add(ent<=1)
        model.Add(sal<=1)
        model.Add(usado[n]==ent)

    cands=[n for n in nodos if n not in (start,goal)]
    for i in range(len(cands)):
        for j in range(i+1,len(cands)):
            a,b=cands[i],cands[j]
            if se_solapan(a,b):
                model.Add(usado[a]+usado[b] <= 1)

    model.Add(sum(z.values())==L_OBJETIVO)

    subidas=[]
    bajadas=[]
    for (o,d),var in z.items():
        dy=d[1]-o[1]
        if dy>0:
            subidas.append(var)
        elif dy<0:
            bajadas.append(var)

    model.Add(sum(subidas)==SUBIDAS_OBJETIVO)
    model.Add(sum(bajadas)==BAJADAS_OBJETIVO)

    for (o,d),var in z.items():
        model.Add(usado[o]+usado[d] <= 1 + var)

    solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=MAX_TIEMPO
    solver.parameters.random_seed=SEED
    solver.parameters.num_search_workers=8

    status=solver.Solve(model)

    ruta=None
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        saltos=[(o,d) for (o,d),var in z.items() if solver.Value(var)==1]
        siguiente={o:d for o,d in saltos}
        ruta=[start]
        actual=start
        while actual!=goal:
            actual=siguiente[actual]
            ruta.append(actual)

    return {
        "ancho":ancho,
        "status":solver.StatusName(status),
        "tiempo":solver.WallTime(),
        "candidatas":len(candidatas),
        "aristas":contar_aristas(grafo),
        "ruta":ruta,
    }

def ejecutar():
    print("="*88)
    print("CASO 2 — BUSQUEDA DEL TAMANO MINIMO SIN ATAJOS")
    print("="*88)

    for ancho in TAMANOS:
        r=resolver(ancho)
        print(f"\nMapa {ancho}x{ALTO}")
        print(f"Variables QUBO previstas: {r['aristas']}")
        print(f"Estado: {r['status']}")
        print(f"Tiempo: {r['tiempo']:.4f} s")
        print(f"Existe solucion sin atajos: {'SI' if r['ruta'] else 'NO'}")
        if r["ruta"]:
            print("Ruta:")
            print(" -> ".join(str(p) for p in r["ruta"]))

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)

    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"busqueda_tamano_minimo_antiatajos_{marca}.txt")

    original=sys.stdout

    class Tee:
        def __init__(self,*s): self.s=s
        def write(self,d):
            for x in self.s:
                x.write(d)
                x.flush()
        def flush(self):
            for x in self.s:
                x.flush()

    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original

    print(f"\nTXT generado correctamente: {ruta}")