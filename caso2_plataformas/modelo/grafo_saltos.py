from collections import deque

SALTO_HORIZONTAL_MAX = 4
SUBIDA_MAX = 2
CAIDA_MAX = 3


def puede_saltar(origen, destino):
    x1, y1 = origen
    x2, y2 = destino

    dx = x2 - x1
    dy = y2 - y1

    return (
        1 <= dx <= SALTO_HORIZONTAL_MAX
        and -CAIDA_MAX <= dy <= SUBIDA_MAX
    )


def construir_grafo_saltos(posiciones):
    posiciones = list(posiciones)
    grafo = {p: [] for p in posiciones}

    for origen in posiciones:
        for destino in posiciones:
            if origen != destino and puede_saltar(origen, destino):
                grafo[origen].append(destino)

    return grafo


def buscar_camino_bfs(grafo, inicio, meta):
    if inicio not in grafo or meta not in grafo:
        return None

    cola = deque([inicio])
    anterior = {inicio: None}

    while cola:
        actual = cola.popleft()

        if actual == meta:
            break

        for siguiente in grafo.get(actual, []):
            if siguiente not in anterior:
                anterior[siguiente] = actual
                cola.append(siguiente)

    if meta not in anterior:
        return None

    camino = []
    actual = meta
    while actual is not None:
        camino.append(actual)
        actual = anterior[actual]

    camino.reverse()
    return camino


def contar_aristas(grafo):
    return sum(len(destinos) for destinos in grafo.values())