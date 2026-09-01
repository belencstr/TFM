import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.escenario_base import (
    ANCHO, ALTO, START, GOAL,
    obtener_candidatas, crear_mapa_ascii,
)
from modelo.grafo_saltos import (
    construir_grafo_saltos,
    buscar_camino_bfs,
    contar_aristas,
)
from solvers.generador_plataformas_cpsat_v2 import generar_ruta_cpsat_v2


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


def construir_subgrafo_inducido(grafo_completo, nodos):
    nodos = set(nodos)
    return {
        origen: [
            destino for destino in grafo_completo.get(origen, [])
            if destino in nodos
        ]
        for origen in nodos
    }


def ejecutar():
    candidatas = obtener_candidatas()
    posiciones = [START] + candidatas + [GOAL]
    grafo = construir_grafo_saltos(posiciones)

    resultado = generar_ruta_cpsat_v2(
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

    print("=" * 86)
    print("CASO 2 — CP-SAT V2: RUTA SIN ATAJOS")
    print("=" * 86)
    print(f"Cuadrícula: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Candidatas potenciales: {len(candidatas)}")
    print(f"Aristas potenciales: {contar_aristas(grafo)}")
    print()
    print(f"Estado CP-SAT: {resultado['status']}")
    print(f"Tiempo CP-SAT: {resultado['tiempo']:.4f} s")

    if resultado["ruta"] is None:
        print("No se ha encontrado solución.")
        return

    ruta = resultado["ruta"]

    print(f"Número de saltos CP-SAT: {resultado['num_saltos']}")
    print(f"Plataformas intermedias: {len(ruta) - 2}")
    print(f"Subidas: {resultado['num_subidas']}")
    print(f"Bajadas: {resultado['num_bajadas']}")
    print(f"Planos: {resultado['num_planos']}")
    print(f"Variación vertical total: {resultado['variacion_vertical']}")
    print()
    print("Ruta CP-SAT:")
    print(" -> ".join(str(p) for p in ruta))
    print()

    subgrafo = construir_subgrafo_inducido(
        grafo,
        resultado["nodos_usados"],
    )
    camino_bfs = buscar_camino_bfs(subgrafo, START, GOAL)

    print("Verificación independiente con BFS:")
    print(f"  existe START -> GOAL: {camino_bfs is not None}")
    if camino_bfs is not None:
        saltos_bfs = len(camino_bfs) - 1
        print(f"  longitud mínima real: {saltos_bfs}")
        print(
            "  coincide con CP-SAT: "
            f"{saltos_bfs == resultado['num_saltos']}"
        )
        print("  camino BFS:")
        print("  " + " -> ".join(str(p) for p in camino_bfs))
    print()

    seleccionadas = [
        p for p in resultado["nodos_usados"]
        if p not in (START, GOAL)
    ]

    print("Mapa generado:")
    print(crear_mapa_ascii(seleccionadas=seleccionadas))
    print()

    print("Camino real marcado con *:")
    print(
        crear_mapa_ascii(
            seleccionadas=seleccionadas,
            camino=camino_bfs or [],
        )
    )


def main():
    carpeta = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(
        carpeta,
        f"caso2_cpsat_v2_sin_atajos_{ANCHO}x{ALTO}_{marca}.txt",
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