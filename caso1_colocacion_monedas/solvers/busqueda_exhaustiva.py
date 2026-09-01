"""Búsqueda exhaustiva exacta para k-medoids/p-median.

Enumera todas las combinaciones de k candidatas y devuelve la que minimiza
la suma de distancias de cada candidata a su medoide más cercano.

Se utiliza únicamente como referencia exacta en instancias pequeñas.
"""

from itertools import combinations
from statistics import mean


def _coste_total(indices_medoides, matriz_distancias):
    return sum(
        min(matriz_distancias[i][m] for m in indices_medoides)
        for i in range(len(matriz_distancias))
    )


def _metricas(indices_medoides, matriz_distancias):
    dist_cobertura = [
        min(matriz_distancias[i][m] for m in indices_medoides)
        for i in range(len(matriz_distancias))
    ]

    separaciones = []
    for pos, i in enumerate(indices_medoides):
        for j in indices_medoides[pos + 1:]:
            separaciones.append(matriz_distancias[i][j])

    return {
        "distancia_media_cobertura": mean(dist_cobertura),
        "radio_cobertura": max(dist_cobertura),
        "separacion_minima": min(separaciones) if separaciones else 0,
        "separacion_media": mean(separaciones) if separaciones else 0.0,
        "separacion_total": sum(separaciones),
    }


def k_medoids_exhaustivo(candidatas, matriz_distancias, k):
    """Obtiene el óptimo global enumerando todas las combinaciones de k medoides."""
    n = len(candidatas)

    if not 1 <= k <= n:
        raise ValueError(f"k debe estar entre 1 y {n}.")

    mejor_coste = None
    mejores_indices = None
    combinaciones_evaluadas = 0

    for indices in combinations(range(n), k):
        combinaciones_evaluadas += 1
        coste = _coste_total(indices, matriz_distancias)

        if mejor_coste is None or coste < mejor_coste:
            mejor_coste = coste
            mejores_indices = indices

    metricas = _metricas(mejores_indices, matriz_distancias)

    return {
        "indices": list(mejores_indices),
        "candidatas": [candidatas[i] for i in mejores_indices],
        "coste_total": mejor_coste,
        "combinaciones_evaluadas": combinaciones_evaluadas,
        **metricas,
    }
