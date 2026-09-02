import os, sys, time
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA, SUBIDA_MAX, CAIDA_MAX,
    obtener_anclas_candidatas, construir_grafo_segmentos_v4
)
from cuantico.formulacion.qubo_caso2_equivalente import construir_qubo_equivalente
from cuantico.solvers.simulated_annealing import resolver_qubo_sa

ANCHO=18
ALTO=5
START=(0,2)
GOAL=(17,2)
MIN_SALTOS=4
MAX_SALTOS=5
MIN_SUBIDAS=2
MIN_BAJADAS=2
NUM_READS=100
NUM_SWEEPS=10000
SEED=20260901

class Tee:
    def __init__(self,*s): self.s=s
    def write(self,d):
        for x in self.s: x.write(d); x.flush()
    def flush(self):
        for x in self.s: x.flush()

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)

    print("="*90)
    print("CASO 2 — PRUEBA SA SOBRE QUBO EQUIVALENTE")
    print("="*90)

    t0=time.perf_counter()
    Q,offset,meta=construir_qubo_equivalente(
        grafo=grafo,
        candidatas=candidatas,
        start=START,
        goal=GOAL,
        ancho_plataforma=ANCHO_PLATAFORMA,
        min_saltos=MIN_SALTOS,
        max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
        max_subida_fisica=SUBIDA_MAX,
        max_caida_fisica=CAIDA_MAX,
    )
    t_build=time.perf_counter()-t0

    print(f"Variables QUBO: {meta['n_variables_total']}")
    print(f"Terminos QUBO: {meta['n_terminos_qubo']}")
    print(f"P: {meta['P']}")
    print(f"Tiempo construccion: {t_build:.3f} s")
    print(f"Ejecutando SA: {NUM_READS} reads, {NUM_SWEEPS} sweeps")

    t1=time.perf_counter()
    ss=resolver_qubo_sa(Q,num_reads=NUM_READS,num_sweeps=NUM_SWEEPS,seed=SEED)
    t_sa=time.perf_counter()-t1

    energias=[float(d.energy)+float(offset) for d in ss.data(fields=["energy"])]
    mejor=min(energias)
    peor=max(energias)

    print()
    print(f"Tiempo SA: {t_sa:.3f} s")
    print(f"Tiempo total: {t_build+t_sa:.3f} s")
    print(f"Energia minima real: {mejor}")
    print(f"Energia maxima real: {peor}")
    print("Referencia optima conocida: 4")

    if abs(mejor-4.0)<1e-8:
        print("SA encuentra energia optima 4.")
    else:
        print("SA no alcanza energia 4 en esta prueba minima.")

def main():
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"prueba_sa_qubo_equivalente_18x5_{NUM_READS}reads_{NUM_SWEEPS}sweeps_{marca}.txt")
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

if __name__=="__main__":
    main()