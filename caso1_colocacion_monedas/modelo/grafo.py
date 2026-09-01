# ============================================================
# CASO 1 - GRAFO DE NAVEGACIÓN
# ============================================================
#
# El grafo representa el movimiento posible dentro del mapa.
#
# Nodos:
#   Todas las celdas transitables: ".", "S" y "E".
#
# Aristas:
#   Dos nodos están conectados si sus celdas son vecinas
#   ortogonalmente: arriba, abajo, izquierda o derecha.
#
# Cada movimiento tiene coste 1.
# ============================================================


CELDAS_TRANSITABLES = {".", "S", "E"}

# Movimiento en 4 direcciones.
DIRECCIONES = [
    (-1, 0),  # arriba
    (1, 0),   # abajo
    (0, -1),  # izquierda
    (0, 1),   # derecha
]


def es_transitable(mapa, fila, columna):
    """
    Comprueba si una posición pertenece al mapa y es transitable.
    """
    if fila < 0 or fila >= len(mapa):
        return False

    if columna < 0 or columna >= len(mapa[0]):
        return False

    return mapa[fila][columna] in CELDAS_TRANSITABLES


def construir_grafo(mapa):
    """
    Construye el grafo de navegación del mapa.

    Devuelve un diccionario de adyacencia:

        {
            (fila, columna): [(fila_vecina, columna_vecina), ...],
            ...
        }

    Cada nodo es una celda transitable.
    """
    grafo = {}

    filas = len(mapa)
    columnas = len(mapa[0])

    if any(len(fila) != columnas for fila in mapa):
        raise ValueError("Todas las filas del mapa deben tener la misma longitud.")

    for fila in range(filas):
        for columna in range(columnas):

            if not es_transitable(mapa, fila, columna):
                continue

            nodo = (fila, columna)
            vecinos = []

            for desplazamiento_fila, desplazamiento_columna in DIRECCIONES:
                fila_vecina = fila + desplazamiento_fila
                columna_vecina = columna + desplazamiento_columna

                if es_transitable(
                    mapa,
                    fila_vecina,
                    columna_vecina,
                ):
                    vecinos.append(
                        (fila_vecina, columna_vecina)
                    )

            grafo[nodo] = vecinos

    return grafo


def contar_aristas(grafo):
    """
    Devuelve el número de aristas no dirigidas del grafo.

    Como cada conexión aparece desde ambos extremos,
    dividimos entre 2.
    """
    total_conexiones = sum(
        len(vecinos)
        for vecinos in grafo.values()
    )

    return total_conexiones // 2


def obtener_componente(grafo, origen):
    """
    Devuelve el conjunto de nodos alcanzables desde 'origen'.

    Se utiliza para comprobar que el mapa forma una única
    región navegable.
    """
    if origen not in grafo:
        raise ValueError(
            f"El nodo de origen {origen} no pertenece al grafo."
        )

    visitados = {origen}
    pendientes = [origen]

    while pendientes:
        actual = pendientes.pop()

        for vecino in grafo[actual]:
            if vecino not in visitados:
                visitados.add(vecino)
                pendientes.append(vecino)

    return visitados


def es_conexo(grafo):
    """
    Comprueba si todas las celdas transitables están conectadas.
    """
    if not grafo:
        return True

    origen = next(iter(grafo))
    alcanzables = obtener_componente(grafo, origen)

    return len(alcanzables) == len(grafo)


def resumen_grafo(grafo):
    """
    Devuelve información básica útil para verificar el grafo.
    """
    return {
        "nodos": len(grafo),
        "aristas": contar_aristas(grafo),
        "conexo": es_conexo(grafo),
    }