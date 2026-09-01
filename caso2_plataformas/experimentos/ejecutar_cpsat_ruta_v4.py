import os, sys
from collections import deque
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import ANCHO, ALTO, START, GOAL
from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA, HUECO_MIN, HUECO_MAX, SUBIDA_MAX, CAIDA_MAX,
    obtener_anclas_candidatas, construir_grafo_segmentos_v4,
    calcular_hueco, contar_aristas,
)
from modelo.visualizacion_segmentos import mapa_segmentos_ascii
from solvers.generador_plataformas_cpsat_v4 import generar_ruta_segmentos_cpsat_v4

MIN_SALTOS = 11
MAX_SALTOS = 14
MIN_SUBIDAS = 2
MIN_BAJADAS = 2
MAX_TIEMPO = 60.0
SEED = 20260825

class Tee:
    def __init__(self,*streams): self.streams=streams
    def write(self,data):
        for s in self.streams:
            s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()

def bfs(grafo, inicio, meta):
    cola=deque([inicio]); anterior={inicio:None}
    while cola:
        actual=cola.popleft()
        if actual==meta: break
        for sig in grafo.get(actual,[]):
            if sig not in anterior:
                anterior[sig]=actual; cola.append(sig)
    if meta not in anterior: return None
    camino=[]; actual=meta
    while actual is not None:
        camino.append(actual); actual=anterior[actual]
    return list(reversed(camino))

def subgrafo_inducido(grafo,nodos):
    nodos=set(nodos)
    return {o:[d for d in grafo.get(o,[]) if d in nodos] for o in nodos}

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)

    resultado=generar_ruta_segmentos_cpsat_v4(
        grafo,START,GOAL,
        min_saltos=MIN_SALTOS,max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,min_bajadas=MIN_BAJADAS,
        max_tiempo=MAX_TIEMPO,seed=SEED,
    )

    print("="*92)
    print("CASO 2 — CP-SAT V4: HUECOS REALES ENTRE PLATAFORMAS")
    print("="*92)
    print(f"Cuadrícula: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Ancho de plataforma: {ANCHO_PLATAFORMA} tiles")
    print(f"Hueco permitido: {HUECO_MIN} .. {HUECO_MAX} tiles vacíos")
    print(f"Subida máxima: {SUBIDA_MAX}")
    print(f"Caída máxima: {CAIDA_MAX}")
    print(f"Anclas candidatas: {len(candidatas)}")
    print(f"Aristas potenciales: {contar_aristas(grafo)}")
    print()
    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Tiempo: {resultado['tiempo']:.4f} s")

    if resultado["ruta"] is None:
        print("No se ha encontrado solución.")
        return

    print(f"Saltos CP-SAT: {resultado['num_saltos']}")
    print(f"Plataformas intermedias: {len(resultado['ruta'])-2}")
    print(f"Subidas: {resultado['num_subidas']}")
    print(f"Bajadas: {resultado['num_bajadas']}")
    print(f"Planos: {resultado['num_planos']}")
    print(f"Variación vertical: {resultado['variacion_vertical']}")
    print()
    print("Ruta:")
    print(" -> ".join(str(p) for p in resultado["ruta"]))
    print()

    huecos=[]
    print("Huecos de cada salto:")
    for o,d in zip(resultado["ruta"][:-1],resultado["ruta"][1:]):
        h=calcular_hueco(o,d,START,GOAL)
        huecos.append(h)
        print(f"  {o} -> {d}: {h} tile(s) vacío(s)")
    print()
    print(f"Hueco mínimo: {min(huecos)}")
    print(f"Hueco máximo: {max(huecos)}")
    print()

    subgrafo=subgrafo_inducido(grafo,resultado["nodos_usados"])
    camino_bfs=bfs(subgrafo,START,GOAL)

    print("Verificación BFS:")
    print(f"  Jugable: {camino_bfs is not None}")
    if camino_bfs is not None:
        saltos_bfs=len(camino_bfs)-1
        print(f"  Saltos mínimos reales: {saltos_bfs}")
        print(f"  Coincide con CP-SAT: {saltos_bfs == resultado['num_saltos']}")
    print()

    anclas=[n for n in resultado["nodos_usados"] if n not in (START,GOAL)]

    print("Mapa generado:")
    print(mapa_segmentos_ascii(ANCHO,ALTO,START,GOAL,anclas=anclas))
    print()
    print("Ruta marcada:")
    print(mapa_segmentos_ascii(
        ANCHO,ALTO,START,GOAL,
        anclas=anclas,
        camino=camino_bfs or [],
    ))

def main():
    carpeta=os.path.join(RAIZ,"resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt=os.path.join(carpeta,f"caso2_cpsat_v4_huecos_{ANCHO}x{ALTO}_{marca}.txt")

    stdout_original=sys.stdout
    try:
        with open(ruta_txt,"w",encoding="utf-8") as f:
            sys.stdout=Tee(stdout_original,f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta_txt}")
    finally:
        sys.stdout=stdout_original

    print(f"\nTXT generado correctamente: {ruta_txt}")

if __name__=="__main__":
    main()