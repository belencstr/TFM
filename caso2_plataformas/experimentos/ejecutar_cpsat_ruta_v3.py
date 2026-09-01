"""Caso 2 — CP-SAT v3 con plataformas horizontales reales."""

import os
import sys
from collections import deque
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import ANCHO, ALTO, START, GOAL

from modelo.grafo_saltos_segmentos import (
    ANCHO_PLATAFORMA,
    obtener_anclas_candidatas,
    construir_grafo_segmentos,
    contar_aristas,
)

from modelo.visualizacion_segmentos import mapa_segmentos_ascii

from solvers.generador_plataformas_cpsat_v3 import (
    generar_ruta_segmentos_cpsat,
)


MIN_SALTOS = 11
MAX_SALTOS = 14
MIN_SUBIDAS = 2
MIN_BAJADAS = 2
MAX_TIEMPO = 60.0
SEED = 20260824


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def bfs(grafo, inicio, meta):
    cola = deque([inicio])
    anterior = {inicio: None}

    while cola:
        actual = cola.popleft()

        if actual == meta:
            break

        for sig in grafo.get(actual, []):
            if sig not in anterior:
                anterior[sig] = actual
                cola.append(sig)

    if meta not in anterior:
        return None

    camino = []
    actual = meta

    while actual is not None:
        camino.append(actual)
        actual = anterior[actual]

    return list(reversed(camino))


def subgrafo_inducido(grafo, nodos):
    nodos = set(nodos)

    return {
        o: [d for d in grafo.get(o, []) if d in nodos]
        for o in nodos
    }


def ejecutar():
    candidatas = obtener_anclas_candidatas(
        ANCHO,
        ALTO,
        START,
        GOAL,
    )

    posiciones = [START] + candidatas + [GOAL]

    grafo = construir_grafo_segmentos(
        posiciones,
        START,
        GOAL,
    )

    resultado = generar_ruta_segmentos_cpsat(
        grafo,
        START,
        GOAL,
        min_saltos=MIN_SALTOS,
        max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
        max_tiempo=MAX_TIEMPO,
        seed=SEED,
    )

    print("=" * 90)
    print("CASO 2 — CP-SAT V3: PLATAFORMAS DE ANCHO REAL")
    print("=" * 90)

    print(f"Cuadrícula: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Ancho de plataforma: {ANCHO_PLATAFORMA} tiles")
    print(f"Anclas candidatas: {len(candidatas)}")
    print(f"Aristas potenciales: {contar_aristas(grafo)}")
    print()

    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Tiempo: {resultado['tiempo']:.4f} s")

    if resultado["ruta"] is None:
        print("No se ha encontrado solución.")
        return

    print(f"Saltos CP-SAT: {resultado['num_saltos']}")
    print(f"Plataformas intermedias: {len(resultado['ruta']) - 2}")
    print(f"Subidas: {resultado['num_subidas']}")
    print(f"Bajadas: {resultado['num_bajadas']}")
    print(f"Planos: {resultado['num_planos']}")
    print(f"Variación vertical: {resultado['variacion_vertical']}")
    print()

    print("Ruta:")
    print(" -> ".join(str(p) for p in resultado["ruta"]))
    print()

    subgrafo = subgrafo_inducido(
        grafo,
        resultado["nodos_usados"],
    )
    camino_bfs = bfs(subgrafo, START, GOAL)

    print("Verificación BFS sobre las plataformas realmente generadas:")
    print(f"  Jugable: {camino_bfs is not None}")

    if camino_bfs is not None:
        print(f"  Saltos mínimos reales: {len(camino_bfs) - 1}")
        print(
            "  Coincide con CP-SAT: "
            f"{len(camino_bfs) - 1 == resultado['num_saltos']}"
        )
    print()

    anclas = [
        n
        for n in resultado["nodos_usados"]
        if n not in (START, GOAL)
    ]

    print("Mapa con plataformas de ancho 2:")
    print(
        mapa_segmentos_ascii(
            ANCHO,
            ALTO,
            START,
            GOAL,
            anclas=anclas,
        )
    )
    print()

    print("Ruta marcada con *:")
    print(
        mapa_segmentos_ascii(
            ANCHO,
            ALTO,
            START,
            GOAL,
            anclas=anclas,
            camino=camino_bfs or [],
        )
    )


def main():
    carpeta = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(
        carpeta,
        f"caso2_cpsat_v3_segmentos_{ANCHO}x{ALTO}_{marca}.txt",
    )

    stdout_original = sys.stdout

    try:
        with open(ruta_txt, "w", encoding="utf-8") as f:
            sys.stdout = Tee(stdout_original, f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta_txt}")
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta_txt}")


if __name__ == "__main__":
    main()