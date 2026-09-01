ANCHO_PLATAFORMA = 2
HUECO_MIN = 1
HUECO_MAX = 4
SUBIDA_MAX = 2
CAIDA_MAX = 3

def obtener_anclas_candidatas(ancho_mapa, alto_mapa, start, goal):
    candidatas = []
    for y in range(alto_mapa):
        for x in range(ancho_mapa - ANCHO_PLATAFORMA + 1):
            celdas = {(cx, y) for cx in range(x, x + ANCHO_PLATAFORMA)}
            if start in celdas or goal in celdas:
                continue
            candidatas.append((x, y))
    return candidatas

def borde_derecho(nodo, start, goal):
    if nodo in (start, goal):
        return nodo[0]
    return nodo[0] + ANCHO_PLATAFORMA - 1

def calcular_hueco(origen, destino, start, goal):
    x_salida = borde_derecho(origen, start, goal)
    x_llegada = destino[0]
    return x_llegada - x_salida - 1

def puede_saltar_segmentos_v4(origen, destino, start, goal):
    if origen == destino:
        return False
    hueco = calcular_hueco(origen, destino, start, goal)
    dy = destino[1] - origen[1]
    return (
        HUECO_MIN <= hueco <= HUECO_MAX
        and -CAIDA_MAX <= dy <= SUBIDA_MAX
    )

def construir_grafo_segmentos_v4(posiciones, start, goal):
    posiciones = list(posiciones)
    grafo = {p: [] for p in posiciones}
    for origen in posiciones:
        for destino in posiciones:
            if puede_saltar_segmentos_v4(origen, destino, start, goal):
                grafo[origen].append(destino)
    return grafo

def contar_aristas(grafo):
    return sum(len(destinos) for destinos in grafo.values())