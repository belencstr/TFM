def obtener_candidatas(mapa):
    """
    Devuelve todas las celdas '.' del mapa como posiciones candidatas.

    S y E son transitables, pero se reservan y no se consideran
    candidatas para colocar monedas.

    Cada candidata se representa como:
        {
            "id": "C001",
            "fila": 1,
            "columna": 2
        }
    """
    resultado = []
    contador = 1

    for fila, contenido in enumerate(mapa):
        for columna, celda in enumerate(contenido):
            if celda == ".":
                resultado.append({
                    "id": f"C{contador:03d}",
                    "fila": fila,
                    "columna": columna,
                })
                contador += 1

    return resultado


def obtener_inicio_fin(mapa):
    """Devuelve las coordenadas (fila, columna) de S y E."""
    inicio = None
    fin = None

    for fila, contenido in enumerate(mapa):
        for columna, celda in enumerate(contenido):
            if celda == "S":
                inicio = (fila, columna)
            elif celda == "E":
                fin = (fila, columna)

    return inicio, fin
