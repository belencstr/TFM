"""Algoritmo de Gonzalez (farthest-first traversal) para k-center discreto.

El objetivo es seleccionar k posiciones candidatas que minimicen el radio de
cobertura máximo respecto al conjunto completo de candidatas.

Se utiliza una variante multiinicio: se ejecuta Gonzalez tomando cada candidata
como centro inicial y se conserva la solución con menor radio de cobertura.
"""

from statistics import mean


def _validar_entrada(candidatas, matriz_distancias, k):
    n = len(candidatas)

    if n == 0:
        raise ValueError("No hay posiciones candidatas.")
    if not 1 <= k <= n:
        raise ValueError(f"k debe estar entre 1 y {n}.")
    if len(matriz_distancias) != n:
        raise ValueError("La matriz de distancias no coincide con las candidatas.")
    if any(len(fila) != n for fila in matriz_distancias):
        raise ValueError("La matriz de distancias debe ser cuadrada.")


def radio_cobertura(indices_seleccionados, matriz_distancias):
    """Calcula R(S) = max_v min_s d(v, s)."""
    if not indices_seleccionados:
        raise ValueError("La solución debe contener al menos un centro.")

    n = len(matriz_distancias)
    return max(
        min(matriz_distancias[i][j] for j in indices_seleccionados)
        for i in range(n)
    )


def separaciones(indices_seleccionados, matriz_distancias):
    """Devuelve separación mínima, media y total entre centros seleccionados."""
    distancias = []
    for pos_i, i in enumerate(indices_seleccionados):
        for j in indices_seleccionados[pos_i + 1:]:
            distancias.append(matriz_distancias[i][j])

    if not distancias:
        return {
            "minima": 0,
            "media": 0.0,
            "total": 0,
        }

    return {
        "minima": min(distancias),
        "media": mean(distancias),
        "total": sum(distancias),
    }


def gonzalez_desde_inicio(candidatas, matriz_distancias, k, indice_inicio):
    """Ejecuta farthest-first traversal desde una candidata concreta.

    En cada iteración se selecciona la candidata cuya distancia a su centro
    seleccionado más cercano sea máxima.

    Los empates se resuelven por índice para obtener resultados reproducibles.
    """
    _validar_entrada(candidatas, matriz_distancias, k)
    n = len(candidatas)

    if not 0 <= indice_inicio < n:
        raise ValueError("El índice inicial no pertenece al conjunto de candidatas.")

    seleccionados = [indice_inicio]
    seleccionados_set = {indice_inicio}

    # Distancia de cada candidata al centro seleccionado más cercano.
    distancia_al_centro_mas_cercano = [
        matriz_distancias[i][indice_inicio]
        for i in range(n)
    ]

    while len(seleccionados) < k:
        siguiente = max(
            (i for i in range(n) if i not in seleccionados_set),
            key=lambda i: (distancia_al_centro_mas_cercano[i], -i),
        )

        seleccionados.append(siguiente)
        seleccionados_set.add(siguiente)

        # Solo hace falta actualizar la distancia al centro más cercano.
        for i in range(n):
            nueva_distancia = matriz_distancias[i][siguiente]
            if nueva_distancia < distancia_al_centro_mas_cercano[i]:
                distancia_al_centro_mas_cercano[i] = nueva_distancia

    radio = max(distancia_al_centro_mas_cercano)
    metricas_sep = separaciones(seleccionados, matriz_distancias)

    return {
        "indices": seleccionados,
        "candidatas": [candidatas[i] for i in seleccionados],
        "radio_cobertura": radio,
        "separacion_minima": metricas_sep["minima"],
        "separacion_media": metricas_sep["media"],
        "separacion_total": metricas_sep["total"],
        "indice_inicio": indice_inicio,
        "id_inicio": candidatas[indice_inicio]["id"],
    }


def gonzalez_multiinicio(candidatas, matriz_distancias, k):
    """Ejecuta Gonzalez desde todas las candidatas y devuelve la mejor solución.

    Criterio principal: menor radio de cobertura.
    Desempates: mayor separación mínima, mayor separación media y, finalmente,
    menor índice de inicio para reproducibilidad.
    """
    _validar_entrada(candidatas, matriz_distancias, k)

    mejor = None

    for indice_inicio in range(len(candidatas)):
        solucion = gonzalez_desde_inicio(
            candidatas,
            matriz_distancias,
            k,
            indice_inicio,
        )

        clave = (
            solucion["radio_cobertura"],
            -solucion["separacion_minima"],
            -solucion["separacion_media"],
            solucion["indice_inicio"],
        )

        if mejor is None or clave < mejor[0]:
            mejor = (clave, solucion)

    return mejor[1]
