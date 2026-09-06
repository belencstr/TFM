"""Experimento comparativo: QUBO Desacoplado vs QUBO Integrado vs CP-SAT.

Genera la tabla comparativa definitiva del Caso 3 para la memoria del TFM:
- Modelo clásico exacto: CP-SAT v3
- QUBO Desacoplado (48 variables, validación clásica de navegabilidad)
- QUBO Integrado (96 variables, ruta garantizada dentro del Hamiltoniano)

Métricas:
- Número de variables binarias.
- Número de términos cuadráticos.
- Tiempo medio de cómputo.
- Tasa de factibilidad geométrica (zonas).
- Tasa de navegabilidad (ruta válida START->GOAL).
- Valor de la función objetivo (fronteras de Ising).
"""

from datetime import datetime
from pathlib import Path
from time import perf_counter
import numpy as np
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clasico.caso3_cpsat_v3 import solve_case3
from formulacion.qubo_caso3 import construir_qubo_geometria
from formulacion.qubo_caso3_integrado import construir_qubo_integrado
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

NUM_READS = 100
NUM_SWEEPS = 1500
SEED = 42


def ejecutar_comparativa():
    print("=" * 70)
    print("CASO 3 — COMPARATIVA METODOLÓGICA DEFINITIVA")
    print("CP-SAT v3 vs QUBO Desacoplado vs QUBO Integrado")
    print("=" * 70)
    print()

    # -------------------------------------------------------------------------
    # 1. CP-SAT v3 (Baseline clásico exacto)
    # -------------------------------------------------------------------------
    print("1. Ejecutando CP-SAT v3...")
    t0 = perf_counter()
    res_cpsat = solve_case3(seed=SEED)
    tiempo_cpsat = perf_counter() - t0

    # -------------------------------------------------------------------------
    # 2. QUBO Desacoplado (Geometría Ising + Validación BFS)
    # -------------------------------------------------------------------------
    print("2. Ejecutando QUBO Desacoplado con Simulated Annealing...")
    qubo_des = construir_qubo_geometria()
    res_des = resolver_qubo_sa(qubo_des, num_reads=NUM_READS, num_sweeps=NUM_SWEEPS, seed=SEED)

    # -------------------------------------------------------------------------
    # 3. QUBO Integrado (Geometría + Variables de Ruta Embebidas)
    # -------------------------------------------------------------------------
    print("3. Ejecutando QUBO Integrado con Simulated Annealing...")
    qubo_int = construir_qubo_integrado()
    res_int = resolver_qubo_sa(qubo_int, num_reads=NUM_READS, num_sweeps=NUM_SWEEPS, seed=SEED)

    # -------------------------------------------------------------------------
    # 4. Tabla Resumen y Comparativa
    # -------------------------------------------------------------------------
    mejor_des = res_des["mejor_muestra"]
    mejor_int = res_int["mejor_muestra"]

    print()
    print("=" * 70)
    print("TABLA COMPARATIVA DE RESULTADOS")
    print("=" * 70)
    print(f"{'Métrica':<32} | {'CP-SAT v3':<12} | {'QUBO Desacop.':<13} | {'QUBO Integ.':<12}")
    print("-" * 75)
    print(f"{'Variables binarias':<32} | {'~150 vars':<12} | {res_des['num_variables']:<13} | {res_int['num_variables']:<12}")
    print(f"{'Términos cuadráticos':<32} | {'N/A (lineal)':<12} | {res_des['num_terminos_cuadraticos']:<13} | {res_int['num_terminos_cuadraticos']:<12}")
    print(f"{'Tiempo de resolución':<32} | {res_cpsat['time']:.3f} s      | {res_des['tiempo_segundos']:.3f} s        | {res_int['tiempo_segundos']:.3f} s")
    print(f"{'Fronteras (Ising)':<32} | {int(res_cpsat['objective']):<12} | {mejor_des['fronteras']:<13} | {mejor_int['fronteras']:<12}")
    print(f"{'Factibilidad de zonas':<32} | {'100% (Exacto)':<12} | {res_des['tasa_factibilidad_zonas']*100:.1f}%        | {res_int['tasa_factibilidad_zonas']*100:.1f}%")
    print(f"{'Tasa de mapas navegables':<32} | {'100% (Garant)':<12} | {res_des['tasa_factibilidad_navegable']*100:.1f}%        | {res_int['tasa_factibilidad_navegable']*100:.1f}%")
    l_cpsat = str(len(res_cpsat['bfs_path']) - 1) if res_cpsat['bfs_path'] else "N/A"
    l_des = str(mejor_des['longitud_bfs']) if mejor_des['longitud_bfs'] is not None else "No ruta"
    l_int = str(mejor_int['longitud_bfs']) if mejor_int['longitud_bfs'] is not None else "No ruta"
    print(f"{'Longitud camino BFS':<32} | {l_cpsat:<12} | {l_des:<13} | {l_int:<12}")
    print(f"{'Componentes conexas':<32} | {res_cpsat['components']:<12} | {mejor_des['componentes']:<13} | {mejor_int['componentes']:<12}")
    print("=" * 70)

    # Guardar informe
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_txt = RESULTADOS_DIR / f"comparativa_cpsat_vs_qubos_{timestamp}.txt"

    lineas = [
        "===========================================================================",
        "CASO 3 — COMPARATIVA DEFINITIVA: CP-SAT vs QUBO DESACOPLADO vs QUBO INTEGRADO",
        "===========================================================================",
        f"Fecha: {timestamp}",
        f"Cuadrícula: 6x8 (48 celdas)",
        f"Parámetros SA: Reads={NUM_READS}, Sweeps={NUM_SWEEPS}, Semilla={SEED}",
        "",
        f"{'Métrica':<32} | {'CP-SAT v3':<14} | {'QUBO Desacoplado':<16} | {'QUBO Integrado':<14}",
        "-" * 82,
        f"{'Variables binarias':<32} | {'~150':<14} | {res_des['num_variables']:<16} | {res_int['num_variables']:<14}",
        f"{'Términos cuadráticos':<32} | {'N/A':<14} | {res_des['num_terminos_cuadraticos']:<16} | {res_int['num_terminos_cuadraticos']:<14}",
        f"{'Tiempo de resolución (s)':<32} | {res_cpsat['time']:<14.4f} | {res_des['tiempo_segundos']:<16.4f} | {res_int['tiempo_segundos']:<14.4f}",
        f"{'Fronteras suelo/pared (Ising)':<32} | {int(res_cpsat['objective']):<14} | {mejor_des['fronteras']:<16} | {mejor_int['fronteras']:<14}",
        f"{'Factibilidad de zonas (%)':<32} | {'100.0':<14} | {res_des['tasa_factibilidad_zonas']*100:<16.1f} | {res_int['tasa_factibilidad_zonas']*100:<14.1f}",
        f"{'Tasa mapas navegables (%)':<32} | {'100.0':<14} | {res_des['tasa_factibilidad_navegable']*100:<16.1f} | {res_int['tasa_factibilidad_navegable']*100:<14.1f}",
        f"{'Longitud camino BFS':<32} | {l_cpsat:<14} | {l_des:<16} | {l_int:<14}",
        f"{'Componentes de suelo':<32} | {res_cpsat['components']:<14} | {mejor_des['componentes']:<16} | {mejor_int['componentes']:<14}",
        "=" * 82,
    ]

    archivo_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe comparativo guardado en: {archivo_txt}")

    return archivo_txt


if __name__ == "__main__":
    ejecutar_comparativa()
