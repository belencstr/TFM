"""Utilidades ASCII para plataformas de ancho fijo."""

from modelo.grafo_saltos_segmentos import ANCHO_PLATAFORMA


def mapa_segmentos_ascii(
    ancho,
    alto,
    start,
    goal,
    anclas=None,
    camino=None,
):
    anclas = set(anclas or [])
    camino = set(camino or [])

    grid = [["." for _ in range(ancho)] for _ in range(alto)]

    # Plataformas generadas.
    for x, y in anclas:
        for dx in range(ANCHO_PLATAFORMA):
            xx = x + dx
            if 0 <= xx < ancho:
                grid[y][xx] = "#"

    # Anclas pertenecientes al camino.
    for nodo in camino:
        if nodo in (start, goal):
            continue

        x, y = nodo
        for dx in range(ANCHO_PLATAFORMA):
            xx = x + dx
            if 0 <= xx < ancho:
                grid[y][xx] = "*"

    sx, sy = start
    gx, gy = goal
    grid[sy][sx] = "S"
    grid[gy][gx] = "G"

    return "\n".join(
        "".join(grid[y])
        for y in reversed(range(alto))
    )