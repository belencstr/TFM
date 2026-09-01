"""Grafo de saltos entre plataformas horizontales de ancho fijo.

Cada candidata (x, y) representa ahora el extremo izquierdo de una plataforma
horizontal de ANCHO_PLATAFORMA tiles.

El salto se calcula desde el borde derecho de la plataforma de origen hasta el
borde izquierdo de la plataforma de destino. START y GOAL siguen siendo puntos.
"""

ANCHO_PLATAFORMA = 2

SALTO_HORIZONTAL_MAX = 4
SUBIDA_MAX = 2
CAIDA_MAX = 3


def intervalo_plataforma(ancla):
    x, y = ancla
    return x, x + ANCHO_PLATAFORMA - 1, y


def obtener_anclas_candidatas(ancho_mapa, alto_mapa, start, goal):
    """Todas las posibles anclas de plataformas de ancho fijo."""
    candidatas = []

    for y in range(alto_mapa):
        for x in range(ancho_mapa - ANCHO_PLATAFORMA + 1):
            ancla = (x, y)

            # Evito que una plataforma tape START o GOAL.
            celdas = {
                (cx, y)
                for cx in range(x, x + ANCHO_PLATAFORMA)
            }

            if start in celdas or goal in celdas:
                continue

            candidatas.append(ancla)

    return candidatas


def borde_derecho(nodo, start, goal):
    if nodo in (start, goal):
        return nodo[0]
    return nodo[0] + ANCHO_PLATAFORMA - 1


def borde_izquierdo(nodo):
    return nodo[0]


def puede_saltar_segmentos(origen, destino, start, goal):
    """Salto físico entre dos plataformas/puntos especiales."""
    if origen == destino:
        return False

    x_salida = borde_derecho(origen, start, goal)
    x_llegada = borde_izquierdo(destino)

    dx = x_llegada - x_salida
    dy = destino[1] - origen[1]

    return (
        1 <= dx <= SALTO_HORIZONTAL_MAX
        and -CAIDA_MAX <= dy <= SUBIDA_MAX
    )


def construir_grafo_segmentos(posiciones, start, goal):
    posiciones = list(posiciones)
    grafo = {p: [] for p in posiciones}

    for origen in posiciones:
        for destino in posiciones:
            if puede_saltar_segmentos(origen, destino, start, goal):
                grafo[origen].append(destino)

    return grafo


def contar_aristas(grafo):
    return sum(len(v) for v in grafo.values())