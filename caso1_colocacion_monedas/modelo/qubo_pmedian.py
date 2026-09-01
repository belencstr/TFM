"""Construcción QUBO para el problema p-median / k-medoids.

Variables:
    x_j = 1 si se selecciona la candidata j como medoide/moneda.
    y_ij = 1 si la candidata i se asigna al medoide j.

Objetivo clásico:
    min sum_{i,j} d_ij y_ij

Restricciones:
    sum_j x_j = k
    sum_j y_ij = 1              para todo i
    y_ij <= x_j                 para todo i,j

QUBO:
    Q(x,y) =
        sum_{i,j} d_ij y_ij
        + A (sum_j x_j - k)^2
        + B sum_i (sum_j y_ij - 1)^2
        + C sum_{i,j} y_ij (1 - x_j)
"""

from collections import defaultdict


def nombre_x(j):
    return f"x_{j}"


def nombre_y(i, j):
    return f"y_{i}_{j}"


def _par_ordenado(a, b):
    """Devuelve una clave estable para un término cuadrático."""
    return tuple(sorted((a, b)))


def construir_qubo_pmedian(
    matriz_distancias,
    k,
    A=None,
    B=None,
    C=None,
    cota_factible=None,
):
    """Construye el QUBO del p-median.

    Si A, B y C no se proporcionan, se usa una penalización común
    P = cota_factible + 1. Esto garantiza, para costes no negativos,
    que cualquier estado que viole al menos una restricción tenga una
    energía mayor que la solución factible usada como cota.

    Parameters
    ----------
    matriz_distancias : list[list[int|float]]
        Matriz cuadrada n x n con distancias no negativas.
    k : int
        Número exacto de monedas/medoides.
    A, B, C : float | None
        Pesos de penalización.
    cota_factible : float | None
        Coste de una solución factible conocida (por ejemplo, PAM).

    Returns
    -------
    dict
        lineal, cuadratico, constante, variables y metadatos.
    """
    n = len(matriz_distancias)

    if n == 0:
        raise ValueError("La matriz de distancias no puede estar vacía.")
    if any(len(fila) != n for fila in matriz_distancias):
        raise ValueError("La matriz de distancias debe ser cuadrada.")
    if any(d < 0 for fila in matriz_distancias for d in fila):
        raise ValueError("Las distancias deben ser no negativas.")
    if not 1 <= k <= n:
        raise ValueError(f"k debe estar entre 1 y {n}.")

    if A is None or B is None or C is None:
        if cota_factible is None:
            raise ValueError(
                "Indica A, B y C explícitamente o proporciona cota_factible."
            )
        P = float(cota_factible) + 1.0
        A = P if A is None else float(A)
        B = P if B is None else float(B)
        C = P if C is None else float(C)
    else:
        A, B, C = float(A), float(B), float(C)

    if A <= 0 or B <= 0 or C <= 0:
        raise ValueError("A, B y C deben ser positivos.")

    lineal = defaultdict(float)
    cuadratico = defaultdict(float)

    # ------------------------------------------------------------
    # 1) Objetivo: sum_{i,j} d_ij y_ij
    # ------------------------------------------------------------
    for i in range(n):
        for j in range(n):
            lineal[nombre_y(i, j)] += float(matriz_distancias[i][j])

    # ------------------------------------------------------------
    # 2) Cardinalidad: A (sum_j x_j - k)^2
    #
    # Como x_j^2 = x_j:
    # A[(1 - 2k) sum_j x_j + 2 sum_{j<l} x_j x_l + k^2]
    # ------------------------------------------------------------
    for j in range(n):
        lineal[nombre_x(j)] += A * (1 - 2 * k)

    for j in range(n):
        for l in range(j + 1, n):
            cuadratico[_par_ordenado(nombre_x(j), nombre_x(l))] += 2 * A

    constante = A * (k ** 2)

    # ------------------------------------------------------------
    # 3) Asignación única:
    # B sum_i (sum_j y_ij - 1)^2
    #
    # Para cada i:
    # B[-sum_j y_ij + 2 sum_{j<l} y_ij y_il + 1]
    # ------------------------------------------------------------
    for i in range(n):
        for j in range(n):
            lineal[nombre_y(i, j)] += -B

        for j in range(n):
            for l in range(j + 1, n):
                cuadratico[
                    _par_ordenado(nombre_y(i, j), nombre_y(i, l))
                ] += 2 * B

        constante += B

    # ------------------------------------------------------------
    # 4) Enlace asignación-apertura:
    # C sum_{i,j} y_ij (1 - x_j)
    # = C sum y_ij - C sum y_ij x_j
    # ------------------------------------------------------------
    for i in range(n):
        for j in range(n):
            y = nombre_y(i, j)
            x = nombre_x(j)
            lineal[y] += C
            cuadratico[_par_ordenado(y, x)] += -C

    variables_x = [nombre_x(j) for j in range(n)]
    variables_y = [nombre_y(i, j) for i in range(n) for j in range(n)]
    variables = variables_x + variables_y

    return {
        "n": n,
        "k": k,
        "A": A,
        "B": B,
        "C": C,
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": float(constante),
        "variables_x": variables_x,
        "variables_y": variables_y,
        "variables": variables,
        "numero_variables": len(variables),
        "numero_terminos_lineales": len(lineal),
        "numero_terminos_cuadraticos": len(cuadratico),
    }


def energia_qubo(qubo, asignacion):
    """Calcula la energía QUBO para una asignación binaria."""
    energia = qubo["constante"]

    for variable, coef in qubo["lineal"].items():
        energia += coef * asignacion.get(variable, 0)

    for (u, v), coef in qubo["cuadratico"].items():
        energia += coef * asignacion.get(u, 0) * asignacion.get(v, 0)

    return energia


def coste_pmedian_desde_asignacion(matriz_distancias, asignacion):
    """Devuelve únicamente el coste original sum d_ij y_ij."""
    n = len(matriz_distancias)
    return sum(
        matriz_distancias[i][j] * asignacion.get(nombre_y(i, j), 0)
        for i in range(n)
        for j in range(n)
    )


def comprobar_factibilidad(qubo, asignacion):
    """Comprueba las tres familias de restricciones del p-median."""
    n = qubo["n"]
    k = qubo["k"]

    seleccionadas = [
        j for j in range(n)
        if asignacion.get(nombre_x(j), 0) == 1
    ]

    cardinalidad_ok = len(seleccionadas) == k

    asignacion_unica_ok = True
    filas_invalidas = []
    for i in range(n):
        total = sum(
            asignacion.get(nombre_y(i, j), 0)
            for j in range(n)
        )
        if total != 1:
            asignacion_unica_ok = False
            filas_invalidas.append((i, total))

    enlace_ok = True
    enlaces_invalidos = []
    for i in range(n):
        for j in range(n):
            y = asignacion.get(nombre_y(i, j), 0)
            x = asignacion.get(nombre_x(j), 0)
            if y == 1 and x == 0:
                enlace_ok = False
                enlaces_invalidos.append((i, j))

    return {
        "factible": cardinalidad_ok and asignacion_unica_ok and enlace_ok,
        "cardinalidad_ok": cardinalidad_ok,
        "asignacion_unica_ok": asignacion_unica_ok,
        "enlace_ok": enlace_ok,
        "seleccionadas": seleccionadas,
        "filas_invalidas": filas_invalidas,
        "enlaces_invalidos": enlaces_invalidos,
    }


def decodificar_solucion(qubo, asignacion):
    """Devuelve una representación legible de una asignación QUBO."""
    n = qubo["n"]
    factibilidad = comprobar_factibilidad(qubo, asignacion)

    asignaciones = {}
    for i in range(n):
        asignaciones[i] = [
            j for j in range(n)
            if asignacion.get(nombre_y(i, j), 0) == 1
        ]

    return {
        **factibilidad,
        "asignaciones": asignaciones,
    }
