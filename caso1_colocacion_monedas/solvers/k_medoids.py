"""k-medoids mediante PAM (Partitioning Around Medoids).

El objetivo es seleccionar k candidatas que minimicen la suma de distancias
navegables desde cada candidata hasta su medoide seleccionado más cercano.

Se implementan las dos fases clásicas de PAM:
1. BUILD: construcción greedy de los k medoides iniciales.
2. SWAP: intercambios medoide/no-medoide mientras reduzcan el coste total.
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


def coste_total(indices_medoides, matriz_distancias):
    """Suma de distancias de cada candidata a su medoide más cercano."""
    if not indices_medoides:
        raise ValueError("Debe existir al menos un medoide.")
    return sum(
        min(matriz_distancias[i][m] for m in indices_medoides)
        for i in range(len(matriz_distancias))
    )


def distancias_a_medoide_mas_cercano(indices_medoides, matriz_distancias):
    """Distancia de cada candidata al medoide seleccionado más próximo."""
    return [
        min(matriz_distancias[i][m] for m in indices_medoides)
        for i in range(len(matriz_distancias))
    ]


def separaciones(indices_seleccionados, matriz_distancias):
    """Separación mínima, media y total entre los medoides seleccionados."""
    distancias = []
    for pos_i, i in enumerate(indices_seleccionados):
        for j in indices_seleccionados[pos_i + 1:]:
            distancias.append(matriz_distancias[i][j])

    if not distancias:
        return {"minima": 0, "media": 0.0, "total": 0}

    return {
        "minima": min(distancias),
        "media": mean(distancias),
        "total": sum(distancias),
    }


def _fase_build(matriz_distancias, k):
    """Fase BUILD de PAM con desempates deterministas por índice."""
    n = len(matriz_distancias)

    # Primer medoide: minimiza la suma de distancias a todas las candidatas.
    primer_medoide = min(
        range(n),
        key=lambda m: (sum(matriz_distancias[i][m] for i in range(n)), m),
    )

    medoides = [primer_medoide]
    conjunto_medoides = {primer_medoide}
    dist_actual = [matriz_distancias[i][primer_medoide] for i in range(n)]
    coste_actual = sum(dist_actual)

    while len(medoides) < k:
        mejor_candidato = None
        mejor_coste = None

        for candidato in range(n):
            if candidato in conjunto_medoides:
                continue

            nuevo_coste = sum(
                min(dist_actual[i], matriz_distancias[i][candidato])
                for i in range(n)
            )

            clave = (nuevo_coste, candidato)
            if mejor_coste is None or clave < mejor_coste:
                mejor_coste = clave
                mejor_candidato = candidato

        medoides.append(mejor_candidato)
        conjunto_medoides.add(mejor_candidato)
        dist_actual = [
            min(dist_actual[i], matriz_distancias[i][mejor_candidato])
            for i in range(n)
        ]
        coste_actual = sum(dist_actual)

    return medoides, coste_actual


def _fase_swap(matriz_distancias, medoides_iniciales):
    """Fase SWAP de PAM hasta alcanzar un óptimo local por intercambios 1-a-1."""
    n = len(matriz_distancias)
    medoides = list(medoides_iniciales)
    coste_actual = coste_total(medoides, matriz_distancias)
    intercambios = 0

    while True:
        conjunto_medoides = set(medoides)
        mejor_movimiento = None

        for posicion, medoide_saliente in enumerate(medoides):
            for candidato_entrante in range(n):
                if candidato_entrante in conjunto_medoides:
                    continue

                propuesta = list(medoides)
                propuesta[posicion] = candidato_entrante
                nuevo_coste = coste_total(propuesta, matriz_distancias)

                # Solo aceptamos mejoras estrictas. Los desempates son
                # deterministas para que el experimento sea reproducible.
                if nuevo_coste < coste_actual:
                    clave = (nuevo_coste, medoide_saliente, candidato_entrante)
                    if mejor_movimiento is None or clave < mejor_movimiento[0]:
                        mejor_movimiento = (
                            clave,
                            posicion,
                            candidato_entrante,
                            nuevo_coste,
                        )

        if mejor_movimiento is None:
            break

        _, posicion, candidato_entrante, coste_actual = mejor_movimiento
        medoides[posicion] = candidato_entrante
        intercambios += 1

    return medoides, coste_actual, intercambios


def k_medoids_pam(candidatas, matriz_distancias, k):
    """Resuelve k-medoids con PAM (BUILD + SWAP).

    Objetivo principal:
        min sum_v min_s d(v, s)

    Devuelve también métricas de cobertura y separación para facilitar la
    comparación con Gonzalez, aunque no formen parte del objetivo de PAM.
    """
    _validar_entrada(candidatas, matriz_distancias, k)

    iniciales, coste_build = _fase_build(matriz_distancias, k)
    finales, coste_final, intercambios = _fase_swap(
        matriz_distancias,
        iniciales,
    )

    distancias_cobertura = distancias_a_medoide_mas_cercano(
        finales,
        matriz_distancias,
    )
    metricas_sep = separaciones(finales, matriz_distancias)

    return {
        "indices": finales,
        "candidatas": [candidatas[i] for i in finales],
        "indices_iniciales": iniciales,
        "candidatas_iniciales": [candidatas[i] for i in iniciales],
        "coste_build": coste_build,
        "coste_total": coste_final,
        "distancia_media_cobertura": mean(distancias_cobertura),
        "radio_cobertura": max(distancias_cobertura),
        "separacion_minima": metricas_sep["minima"],
        "separacion_media": metricas_sep["media"],
        "separacion_total": metricas_sep["total"],
        "intercambios": intercambios,
    }