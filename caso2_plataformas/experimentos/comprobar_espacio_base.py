import os
import sys

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
    SALTO_HORIZONTAL_MAX,
    SUBIDA_MAX,
    CAIDA_MAX,
    construir_grafo_saltos,
    buscar_camino_bfs,
    contar_aristas,
)


def main():
    candidatas = obtener_candidatas()
    posiciones_grafo = [START] + candidatas + [GOAL]

    grafo = construir_grafo_saltos(posiciones_grafo)
    camino = buscar_camino_bfs(grafo, START, GOAL)

    print("=" * 72)
    print("CASO 2 — COMPROBACIÓN DEL ESPACIO BASE")
    print("=" * 72)
    print(f"Dimensiones: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Posiciones candidatas: {len(candidatas)}")
    print()

    print("Reglas de salto:")
    print(f"  avance horizontal máximo: {SALTO_HORIZONTAL_MAX}")
    print(f"  subida máxima: {SUBIDA_MAX}")
    print(f"  caída máxima: {CAIDA_MAX}")
    print()

    print(f"Nodos del grafo potencial: {len(grafo)}")
    print(f"Aristas de salto potenciales: {contar_aristas(grafo)}")
    print(f"Existe camino START -> GOAL usando todas las candidatas: {camino is not None}")
    print()

    print("Cuadrícula completa de candidatas:")
    print(crear_mapa_ascii())
    print()

    if camino is not None:
        print(f"Camino BFS más corto usando todas las posiciones: {len(camino) - 1} saltos")
        print("Secuencia:")
        print(" -> ".join(str(p) for p in camino))
        print()
        print("Camino marcado con *:")
        print(crear_mapa_ascii(camino=camino))
    else:
        print("No existe ningún camino con las reglas actuales.")


if __name__ == "__main__":
    main()