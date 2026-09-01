"""Primera generación constraint-based del Caso 2.

Genera una ruta START -> GOAL con CP-SAT y la verifica de manera independiente
mediante BFS sobre el subgrafo formado únicamente por las posiciones generadas.

La salida se guarda también como TXT con marca temporal en resultados/.
"""

import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import (
    ANCHO,
    ALTO,
    START,
    GOAL,
    obtener_candidatas,
    crear_mapa_ascii,
)
from modelo.grafo_saltos import (
    construir_grafo_saltos,
    buscar_camino_bfs,
    contar_aristas,
)
from solvers.generador_plataformas_cpsat import generar_ruta_cpsat


MIN_SALTOS = 11
MAX_SALTOS = 14

MIN_SUBIDAS = 2
MIN_BAJADAS = 2

MAX_TIEMPO = 30.0
SEED = 20260816


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


def construir_subgrafo_ruta(grafo_completo, ruta):
    """Conserva únicamente nodos generados y saltos posibles entre ellos."""
    nodos = set(ruta)

    return {
        origen: [
            destino
            for destino in grafo_completo.get(origen, [])
            if destino in nodos
        ]
        for origen in nodos
    }


def ejecutar():
    candidatas = obtener_candidatas()
    posiciones = [START] + candidatas + [GOAL]

    grafo = construir_grafo_saltos(posiciones)

    resultado = generar_ruta_cpsat(
        grafo=grafo,
        inicio=START,
        meta=GOAL,
        min_saltos=MIN_SALTOS,
        max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,
        min_bajadas=MIN_BAJADAS,
        max_tiempo=MAX_TIEMPO,
        seed=SEED,
    )

    print("=" * 80)
    print("CASO 2 — PRIMERA GENERACIÓN CONSTRAINT-BASED CON CP-SAT")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cuadrícula: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Candidatas potenciales: {len(candidatas)}")
    print(f"Aristas potenciales del grafo: {contar_aristas(grafo)}")
    print()

    print("Restricciones de generación:")
    print(f"  saltos: {MIN_SALTOS} .. {MAX_SALTOS}")
    print(f"  subidas mínimas: {MIN_SUBIDAS}")
    print(f"  bajadas mínimas: {MIN_BAJADAS}")
    print("  máximo de saltos planos consecutivos: 2")
    print()

    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Tiempo CP-SAT: {resultado['tiempo']:.4f} s")

    if resultado["ruta"] is None:
        print("No se ha encontrado una ruta que cumpla las restricciones.")
        return

    ruta = resultado["ruta"]

    print(f"Número de saltos: {resultado['num_saltos']}")
    print(f"Plataformas intermedias: {len(ruta) - 2}")
    print(f"Subidas: {resultado['num_subidas']}")
    print(f"Bajadas: {resultado['num_bajadas']}")
    print(f"Saltos planos: {resultado['num_planos']}")
    print(f"Variación vertical total: {resultado['variacion_vertical']}")
    print()

    print("Ruta generada:")
    print(" -> ".join(str(p) for p in ruta))
    print()

    # ------------------------------------------------------------
    # Verificación independiente mediante BFS
    # ------------------------------------------------------------
    subgrafo = construir_subgrafo_ruta(grafo, ruta)
    camino_bfs = buscar_camino_bfs(subgrafo, START, GOAL)

    print("Verificación independiente:")
    print(f"  BFS encuentra START -> GOAL: {camino_bfs is not None}")

    if camino_bfs is not None:
        print(f"  Saltos del camino BFS: {len(camino_bfs) - 1}")
    print()

    seleccionadas = [
        posicion
        for posicion in ruta
        if posicion not in (START, GOAL)
    ]

    print("Mapa generado:")
    print(crear_mapa_ascii(seleccionadas=seleccionadas))
    print()

    print("Ruta marcada con *:")
    print(crear_mapa_ascii(camino=ruta))


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(
        carpeta_resultados,
        f"caso2_cpsat_ruta_{ANCHO}x{ALTO}_{marca}.txt",
    )

    stdout_original = sys.stdout

    try:
        with open(ruta_txt, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta_txt}")
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta_txt}")


if __name__ == "__main__":
    main()