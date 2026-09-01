ANCHO = 40
ALTO = 10

START = (0, 4)
GOAL = (39, 4)


def obtener_candidatas():
    candidatas = []
    for y in range(ALTO):
        for x in range(ANCHO):
            pos = (x, y)
            if pos in (START, GOAL):
                continue
            candidatas.append(pos)
    return candidatas


def crear_mapa_ascii(seleccionadas=None, camino=None):
    seleccionadas = set(seleccionadas or [])
    camino = set(camino or [])

    filas = []
    for y in reversed(range(ALTO)):
        fila = []
        for x in range(ANCHO):
            pos = (x, y)

            if pos == START:
                simbolo = "S"
            elif pos == GOAL:
                simbolo = "G"
            elif pos in camino:
                simbolo = "*"
            elif pos in seleccionadas:
                simbolo = "#"
            else:
                simbolo = "."

            fila.append(simbolo)
        filas.append("".join(fila))

    return "\n".join(filas)