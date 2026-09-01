"""Validación exacta del QUBO p-median sobre una instancia mínima.

La instancia tiene 3 candidatas y k=2:
    0 --- 1 --- 2

Se enumeran TODOS los estados binarios del QUBO:
    3 variables x
    9 variables y
    total = 12 variables = 4096 estados

La validación comprueba:
1. El óptimo clásico del p-median por enumeración de medoides.
2. El mínimo global del QUBO por enumeración de todos sus estados.
3. Que el mínimo QUBO sea factible.
4. Que su coste original coincida con el óptimo clásico.

Cada ejecución guarda un TXT en la carpeta `resultados/`.
"""

import os
import sys
import time
from datetime import datetime
from itertools import combinations, product

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.qubo_pmedian import (
    construir_qubo_pmedian,
    energia_qubo,
    coste_pmedian_desde_asignacion,
    comprobar_factibilidad,
)


K = 2

MATRIZ_DISTANCIAS = [
    [0, 1, 2],
    [1, 0, 1],
    [2, 1, 0],
]


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def coste_clasico(indices_medoides):
    return sum(
        min(MATRIZ_DISTANCIAS[i][m] for m in indices_medoides)
        for i in range(len(MATRIZ_DISTANCIAS))
    )


def resolver_pmedian_exacto():
    n = len(MATRIZ_DISTANCIAS)
    mejor_coste = None
    mejores = []

    for medoides in combinations(range(n), K):
        coste = coste_clasico(medoides)

        if mejor_coste is None or coste < mejor_coste:
            mejor_coste = coste
            mejores = [medoides]
        elif coste == mejor_coste:
            mejores.append(medoides)

    return mejor_coste, mejores


def resolver_qubo_exacto(qubo):
    variables = qubo["variables"]
    mejor_energia = None
    mejores_asignaciones = []
    estados_evaluados = 0

    for bits in product((0, 1), repeat=len(variables)):
        estados_evaluados += 1
        asignacion = dict(zip(variables, bits))
        energia = energia_qubo(qubo, asignacion)

        if mejor_energia is None or energia < mejor_energia - 1e-9:
            mejor_energia = energia
            mejores_asignaciones = [asignacion]
        elif abs(energia - mejor_energia) <= 1e-9:
            mejores_asignaciones.append(asignacion)

    return mejor_energia, mejores_asignaciones, estados_evaluados


def ejecutar_validacion():
    print("=" * 76)
    print("VALIDACIÓN EXACTA DEL QUBO P-MEDIAN")
    print("=" * 76)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Número de candidatas: {len(MATRIZ_DISTANCIAS)}")
    print(f"k: {K}")
    print("Instancia: tres posiciones en línea")
    print()

    coste_optimo, soluciones_clasicas = resolver_pmedian_exacto()

    print("ÓPTIMO CLÁSICO")
    print(f"Coste óptimo: {coste_optimo}")
    print(f"Selecciones óptimas: {soluciones_clasicas}")
    print()

    # Una solución factible óptima tiene coste 1, por lo que P=2.
    qubo = construir_qubo_pmedian(
        MATRIZ_DISTANCIAS,
        K,
        cota_factible=coste_optimo,
    )

    print("QUBO")
    print(f"A = {qubo['A']}")
    print(f"B = {qubo['B']}")
    print(f"C = {qubo['C']}")
    print(f"Variables x: {len(qubo['variables_x'])}")
    print(f"Variables y: {len(qubo['variables_y'])}")
    print(f"Variables totales: {qubo['numero_variables']}")
    print(f"Estados binarios a evaluar: {2 ** qubo['numero_variables']}")
    print(f"Términos lineales: {qubo['numero_terminos_lineales']}")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print()

    inicio = time.perf_counter()
    energia_minima, minimos, estados = resolver_qubo_exacto(qubo)
    tiempo = time.perf_counter() - inicio

    print("MÍNIMO GLOBAL DEL QUBO")
    print(f"Energía mínima: {energia_minima}")
    print(f"Estados evaluados: {estados}")
    print(f"Número de estados con energía mínima: {len(minimos)}")
    print(f"Tiempo: {tiempo:.6f} s")
    print()

    todos_factibles = True
    costes_minimos = set()

    for numero, asignacion in enumerate(minimos, start=1):
        fact = comprobar_factibilidad(qubo, asignacion)
        coste_original = coste_pmedian_desde_asignacion(
            MATRIZ_DISTANCIAS,
            asignacion,
        )
        costes_minimos.add(coste_original)
        todos_factibles = todos_factibles and fact["factible"]

        print(f"Solución QUBO mínima {numero}:")
        print(f"  Medoides seleccionados: {fact['seleccionadas']}")
        print(f"  Factible: {fact['factible']}")
        print(f"  Coste p-median: {coste_original}")
        print()

    coincide_coste = costes_minimos == {coste_optimo}

    print("=" * 76)
    print("RESULTADO DE LA VALIDACIÓN")
    print("=" * 76)
    print(f"Todos los mínimos QUBO son factibles: {todos_factibles}")
    print(f"Coste mínimo QUBO coincide con p-median: {coincide_coste}")

    if todos_factibles and coincide_coste:
        print()
        print("VALIDACIÓN SUPERADA:")
        print(
            "El mínimo global del QUBO representa una solución factible "
            "y reproduce exactamente el óptimo del p-median."
        )
    else:
        print()
        print("VALIDACIÓN NO SUPERADA:")
        print("La formulación o las penalizaciones deben revisarse.")


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"validacion_qubo_pmedian_k{K}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout
    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_validacion()
            print()
            print("=" * 76)
            print(f"Registro guardado en: {ruta}")
            print("=" * 76)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
