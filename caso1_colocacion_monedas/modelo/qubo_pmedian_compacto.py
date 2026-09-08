"""Construcción QUBO compacta para la instancia p-median con k = 2.

A diferencia de la formulación estándar PLI que introduce n^2 variables auxiliares
de asignación y_ij (llevando a n + n^2 qubits), esta formulación compacta está
diseñada específicamente para estudiar el impacto de la codificación en instancias con k = 2:

    x_j = 1 si se selecciona la candidata j como medoide/moneda.

Fundamento para k = 2:
Al seleccionar exactamente dos monedas, solo existe una única pareja activa x_j x_l = 1.
Por tanto, el coste p-median exacto de cada par {j, l} puede precalcularse analíticamente como:

    C(j, l) = sum_{i=1}^n min(d_ij, d_il)

y escribirse como una forma cuadrática pura sobre las variables de decisión:

    H_obj(x) = sum_{j < l} C(j, l) x_j x_l

Restricción de cardinalidad:
    sum_j x_j = 2
    Penalización: A * (sum_j x_j - 2)^2
                = A * [-3 sum_j x_j + 2 sum_{j < l} x_j x_l + 4]

IMPORTANTE (alcance acotado a k = 2):
Esta propiedad no se generaliza directamente a k > 2 (por ejemplo k = 4), ya que
habría C(k, 2) productos cruzados activos simultáneamente y la suma de costes de
parejas dejaría de coincidir con sum_i min_{j in S} d_ij. Por ello, si k != 2,
el código lanza explícitamente NotImplementedError.

Para n = 4 candidatas y k = 2:
- Requiere 4 variables binarias -> 4 QUBITS (frente a 20 qubits en la codificación con y_ij).
- Espacio de Hilbert: 2^4 = 16 estados (frente a 1.048.576).
- Fracción de estados factibles: C(4, 2) / 16 = 6 / 16 = 37.5% (frente a 0.0092%).
"""

from collections import defaultdict
from itertools import combinations


def nombre_x(j):
    return f"x_{j}"


def _par_ordenado(a, b):
    return tuple(sorted((a, b)))


def calcular_costes_por_pareja(matriz_distancias):
    """Calcula el coste p-median exacto para cada pareja posible de medoides.

    Parameters
    ----------
    matriz_distancias : list[list[int|float]]
        Matriz cuadrada n x n con distancias navegables entre candidatas.

    Returns
    -------
    dict
        Mapeo (j, l) -> coste p-median exacto con j < l.
    """
    n = len(matriz_distancias)
    costes = {}

    for j, l in combinations(range(n), 2):
        coste = sum(min(matriz_distancias[i][j], matriz_distancias[i][l]) for i in range(n))
        costes[(j, l)] = coste

    return costes


def construir_qubo_pmedian_compacto(
    matriz_distancias,
    k=2,
    A=None,
    cota_factible=None,
):
    """Construye el QUBO compacto para p-median con k=2 sobre n variables binarias.

    Parameters
    ----------
    matriz_distancias : list[list[int|float]]
        Matriz de distancias navegables n x n.
    k : int
        Número exacto de medoides/monedas (por defecto k=2).
    A : float | None
        Peso de penalización por violación de cardinalidad.
    cota_factible : float | None
        Coste de una solución factible conocida (por ejemplo, PAM o exhaustivo).

    Returns
    -------
    dict
        lineal, cuadratico, constante, variables y metadatos del QUBO.
    """
    n = len(matriz_distancias)

    if n == 0:
        raise ValueError("La matriz de distancias no puede estar vacía.")
    if any(len(fila) != n for fila in matriz_distancias):
        raise ValueError("La matriz de distancias debe ser cuadrada.")
    if any(d < 0 for fila in matriz_distancias for d in fila):
        raise ValueError("Las distancias deben ser no negativas.")
    if k != 2:
        raise NotImplementedError("La formulación cuadrática exacta directa está implementada para k=2.")

    costes_parejas = calcular_costes_por_pareja(matriz_distancias)
    max_coste = max(costes_parejas.values()) if costes_parejas else 1.0

    if A is None:
        if cota_factible is not None:
            A = float(cota_factible) + 2.0
        else:
            A = float(max_coste) + 2.0
    else:
        A = float(A)

    if A <= 0:
        raise ValueError("A debe ser positivo.")

    lineal = defaultdict(float)
    cuadratico = defaultdict(float)

    # 1) Términos de cardinalidad: A (sum_j x_j - k)^2
    # Como x_j^2 = x_j:
    # A * [(1 - 2k) sum_j x_j + 2 sum_{j < l} x_j x_l + k^2]
    coef_lineal = A * (1.0 - 2.0 * k)
    for j in range(n):
        lineal[nombre_x(j)] += coef_lineal

    for j, l in combinations(range(n), 2):
        cuadratico[_par_ordenado(nombre_x(j), nombre_x(l))] += 2.0 * A

    constante = A * (k ** 2)

    # 2) Función objetivo: sum_{j < l} C(j, l) x_j x_l
    for (j, l), coste in costes_parejas.items():
        cuadratico[_par_ordenado(nombre_x(j), nombre_x(l))] += float(coste)

    variables = [nombre_x(j) for j in range(n)]

    return {
        "n": n,
        "k": k,
        "A": A,
        "costes_parejas": costes_parejas,
        "lineal": dict(lineal),
        "cuadratico": dict(cuadratico),
        "constante": float(constante),
        "variables": variables,
        "numero_variables": len(variables),
        "numero_terminos_lineales": len(lineal),
        "numero_terminos_cuadraticos": len(cuadratico),
    }


def energia_qubo_compacto(qubo, asignacion):
    """Calcula la energía QUBO para una asignación binaria en el modelo compacto."""
    energia = qubo["constante"]

    for var, coef in qubo["lineal"].items():
        energia += coef * asignacion.get(var, 0)

    for (u, v), coef in qubo["cuadratico"].items():
        energia += coef * asignacion.get(u, 0) * asignacion.get(v, 0)

    return energia


def comprobar_factibilidad_compacto(qubo, asignacion):
    """Comprueba si exactamente k variables x_j están activas."""
    n = qubo["n"]
    k = qubo["k"]

    seleccionadas = [j for j in range(n) if asignacion.get(nombre_x(j), 0) == 1]
    factible = (len(seleccionadas) == k)

    return {
        "factible": factible,
        "seleccionadas": seleccionadas,
        "num_seleccionadas": len(seleccionadas),
    }


def coste_pmedian_compacto(matriz_distancias, seleccionadas):
    """Calcula el coste p-median original a partir de los índices de candidatas seleccionadas."""
    if not seleccionadas:
        return None
    n = len(matriz_distancias)
    return sum(min(matriz_distancias[i][m] for m in seleccionadas) for i in range(n))
