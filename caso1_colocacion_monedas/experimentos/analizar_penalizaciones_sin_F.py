import os, sys
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from mapas.mapa_a import MAPA_A
from mapas.mapa_b import MAPA_B
from mapas.mapa_c import MAPA_C
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable
from solvers.k_medoids import k_medoids_pam

def analizar(nombre,mapa,k=4):
    candidatas=obtener_candidatas(mapa)
    grafo=construir_grafo(mapa)
    matriz=construir_matriz_navegable(candidatas,grafo)
    n=len(candidatas)
    dmax=max(float(v) for fila in matriz for v in fila)
    U=sum(max(float(v) for v in fila) for fila in matriz)
    P_teorico=U+1.0
    pam=k_medoids_pam(candidatas,matriz,k)
    P_pam=float(pam["coste_total"])+1.0

    print(f"MAPA {nombre}")
    print(f"  candidatas n: {n}")
    print(f"  d_max: {dmax:g}")
    print(f"  cota simple n*d_max: {n*dmax:g}")
    print(f"  cota U=sum_i max_j d_ij: {U:g}")
    print(f"  P teorico sin resolver p-median: {P_teorico:g}")
    print(f"  PAM solo para comparar: {pam['coste_total']}")
    print(f"  P anterior=PAM+1: {P_pam:g}")
    print()
    return nombre,n,dmax,U,P_teorico,P_pam

def ejecutar():
    print("="*88)
    print("CASO 1 — PENALIZACIONES SIN CONOCER F")
    print("="*88)
    print("Criterio: P = 1 + sum_i max_j d_ij")
    print("Esta cota depende solo de la matriz de distancias y no exige resolver p-median.")
    print()
    resultados=[analizar(n,m) for n,m in (("A",MAPA_A),("B",MAPA_B),("C",MAPA_C))]
    print("Mapa | n | dmax | U teorica | P teorico | P PAM+1")
    for n,nn,dmax,U,P,PP in resultados:
        print(f"{n} | {nn} | {dmax:.0f} | {U:.0f} | {P:.0f} | {PP:.0f}")

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"resultados"); os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"penalizaciones_sin_F_{marca}.txt")
    original=sys.stdout
    class Tee:
        def __init__(self,*s): self.s=s
        def write(self,d):
            for x in self.s: x.write(d); x.flush()
        def flush(self):
            for x in self.s: x.flush()
    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f); ejecutar(); print(); print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original
    print(f"\nTXT generado correctamente: {ruta}")