# ============================================================
# CASO 1 - DISTANCIAS ENTRE POSICIONES CANDIDATAS
# ============================================================
#
# Se implementan dos métricas:
#
# 1. Distancia euclídea:
#       separación geométrica directa entre dos celdas.
#
# 2. Distancia navegable:
#       longitud del camino más corto dentro del mapa,
#       respetando muros y movimiento ortogonal.
#
# La distancia navegable será la métrica principal del Caso 1.
# ============================================================

from collections import deque
from math import sqrt


def posicion_candidata(candidata):
    """
    Convierte una candidata en una coordenada del mapa.

    Ejemplo:
        {"id": "C001", "fila": 1, "columna": 2}
        -> (1, 2)
    """
    return candidata["fila"], candidata["columna"]


def distancia_euclidea(posicion_a, posicion_b):
    """
    Calcula la distancia euclídea entre dos posiciones
    (fila, columna).
    """
    fila_a, columna_a = posicion_a
    fila_b, columna_b = posicion_b

    diferencia_filas = fila_a - fila_b
    diferencia_columnas = columna_a - columna_b

    return sqrt(
        diferencia_filas ** 2
        + diferencia_columnas ** 2
    )


def distancias_navegables_desde(grafo, origen):
    """
    Calcula mediante BFS la distancia mínima desde 'origen'
    hasta todos los nodos alcanzables del grafo.

    Como cada arista representa un movimiento de coste 1,
    BFS proporciona el camino más corto.

    Devuelve:
        {
            nodo: distancia_desde_origen,
            ...
        }
    """
    if origen not in grafo:
        raise ValueError(
            f"El origen {origen} no pertenece al grafo."
        )

    distancias = {origen: 0}
    pendientes = deque([origen])

    while pendientes:
        actual = pendientes.popleft()

        for vecino in grafo[actual]:
            if vecino not in distancias:
                distancias[vecino] = distancias[actual] + 1
                pendientes.append(vecino)

    return distancias


def distancia_navegable(grafo, origen, destino):
    """
    Devuelve la longitud del camino navegable más corto
    entre dos posiciones.

    Si el destino no es alcanzable, devuelve None.
    """
    distancias = distancias_navegables_desde(
        grafo,
        origen,
    )

    return distancias.get(destino)


def construir_matriz_euclidea(candidatas):
    """
    Construye la matriz completa de distancias euclídeas.

    El orden de filas y columnas coincide con el orden
    de la lista 'candidatas'.

    Si candidatas[0] es C001 y candidatas[1] es C002:
        matriz[0][1] = distancia(C001, C002)
    """
    numero_candidatas = len(candidatas)

    matriz = [
        [0.0 for _ in range(numero_candidatas)]
        for _ in range(numero_candidatas)
    ]

    for i in range(numero_candidatas):
        posicion_i = posicion_candidata(candidatas[i])

        for j in range(i + 1, numero_candidatas):
            posicion_j = posicion_candidata(candidatas[j])

            distancia = distancia_euclidea(
                posicion_i,
                posicion_j,
            )

            # La matriz de distancias es simétrica.
            matriz[i][j] = distancia
            matriz[j][i] = distancia

    return matriz


def construir_matriz_navegable(candidatas, grafo):
    """
    Construye la matriz completa de distancias navegables.

    Para cada candidata se ejecuta una BFS desde su posición.
    Después se recupera la distancia mínima hasta el resto
    de candidatas.

    Si el mapa es conexo, todas las parejas deben tener
    una distancia finita.
    """
    numero_candidatas = len(candidatas)

    matriz = [
        [0 for _ in range(numero_candidatas)]
        for _ in range(numero_candidatas)
    ]

    posiciones = [
        posicion_candidata(candidata)
        for candidata in candidatas
    ]

    for i, origen in enumerate(posiciones):
        distancias_desde_origen = distancias_navegables_desde(
            grafo,
            origen,
        )

        for j in range(i + 1, numero_candidatas):
            destino = posiciones[j]

            if destino not in distancias_desde_origen:
                raise ValueError(
                    "Hay candidatas que no están conectadas "
                    f"por el mapa: {origen} -> {destino}"
                )

            distancia = distancias_desde_origen[destino]

            matriz[i][j] = distancia
            matriz[j][i] = distancia

    return matriz


def construir_matrices_distancia(candidatas, grafo):
    """
    Construye ambas matrices para poder compararlas.

    Devuelve:
        {
            "euclidea": [...],
            "navegable": [...]
        }

    La matriz 'navegable' será la utilizada inicialmente
    como matriz D del problema.
    """
    return {
        "euclidea": construir_matriz_euclidea(candidatas),
        "navegable": construir_matriz_navegable(
            candidatas,
            grafo,
        ),
    }


def comprobar_matriz_simetrica(matriz, tolerancia=1e-9):
    """
    Comprueba que una matriz de distancias:
      - sea cuadrada,
      - tenga diagonal igual a cero,
      - sea simétrica.
    """
    n = len(matriz)

    if any(len(fila) != n for fila in matriz):
        return False

    for i in range(n):
        if abs(matriz[i][i]) > tolerancia:
            return False

        for j in range(i + 1, n):
            if abs(matriz[i][j] - matriz[j][i]) > tolerancia:
                return False

    return True