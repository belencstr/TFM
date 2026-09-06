"""Experimento de Robustez: 20 semillas estocásticas para el Caso 3.

Ejecuta Simulated Annealing a lo largo de 20 semillas distintas
para evaluar la estabilidad de la formulación QUBO:
- Tasa media de cumplimiento de zonas.
- Tasa media de navegabilidad START->GOAL.
- Variabilidad del valor objetivo (fronteras de Ising).
- Tiempo medio de cómputo.
"""

from datetime import datetime
from pathlib import Path
import numpy as np
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import construir_qubo_geometria, ROWS, COLS
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

NUM_SEMILLAS = 20
SEMILLAS = [1000 + i * 37 for i in range(NUM_SEMILLAS)]
NUM_READS = 100
NUM_SWEEPS = 1000


def evaluar_robustez(
    peso_frontera=1.0,
    peso_zona=12.0,
    peso_start_goal=50.0,
):
    print("=" * 65)
    print("CASO 3 — EVALUACIÓN DE ROBUSTEZ (20 SEMILLAS ESTOCÁSTICAS)")
    print("=" * 65)
    print(f"Instancia: {ROWS}x{COLS} (48 variables binarias)")
    print(f"Configuración SA: {NUM_READS} reads, {NUM_SWEEPS} sweeps por semilla")
    print()

    qubo = construir_qubo_geometria(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
    )

    resultados_semillas = []

    for idx, seed in enumerate(SEMILLAS, 1):
        res = resolver_qubo_sa(
            qubo,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
        )
        mejor = res["mejor_muestra"]

        resultados_semillas.append({
            "seed": seed,
            "tiempo": res["tiempo_segundos"],
            "tasa_zonas": res["tasa_factibilidad_zonas"],
            "tasa_navegable": res["tasa_factibilidad_navegable"],
            "mejor_energia": mejor["energia"],
            "mejor_fronteras": mejor["fronteras"],
            "mejor_navegable": mejor["es_navegable"],
            "mejor_longitud_bfs": mejor["longitud_bfs"],
            "mejor_componentes": mejor["componentes"],
            "mejor_zonas_ok": mejor["zonas_ok"],
        })

        print(
            f"[{idx:02d}/{NUM_SEMILLAS}] Semilla {seed:5d} | "
            f"Fronteras: {mejor['fronteras']:2d} | "
            f"Zonas: {'OK' if mejor['zonas_ok'] else 'FAIL'} | "
            f"Navegable: {'SI' if mejor['es_navegable'] else 'NO'} | "
            f"Comp: {mejor['componentes']} | "
            f"Tasa Nav: {res['tasa_factibilidad_navegable']*100:4.1f}% | "
            f"Tiempo: {res['tiempo_segundos']:.3f} s"
        )

    # Métricas agregadas
    tiempos = [r["tiempo"] for r in resultados_semillas]
    tasas_zonas = [r["tasa_zonas"] * 100 for r in resultados_semillas]
    tasas_nav = [r["tasa_navegable"] * 100 for r in resultados_semillas]
    fronteras = [r["mejor_fronteras"] for r in resultados_semillas]
    frac_mejores_navegables = sum(1 for r in resultados_semillas if r["mejor_navegable"]) / NUM_SEMILLAS * 100

    print()
    print("=" * 65)
    print("RESUMEN ESTADÍSTICO (20 SEMILLAS)")
    print("=" * 65)
    print(f"Fronteras de mejor solución: media = {np.mean(fronteras):.2f} ± {np.std(fronteras):.2f} "
          f"(min = {min(fronteras)}, max = {max(fronteras)})")
    print(f"Tasa cumplimiento de zonas (por muestra): media = {np.mean(tasas_zonas):.1f}%")
    print(f"Tasa mapas navegables (por muestra): media = {np.mean(tasas_nav):.1f}%")
    print(f"Porcentaje de semillas con mejor muestra navegable: {frac_mejores_navegables:.1f}%")
    print(f"Tiempo medio por semilla: {np.mean(tiempos):.4f} s (Total: {sum(tiempos):.2f} s)")
    print("=" * 65)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_txt = RESULTADOS_DIR / f"robustez_sa_{ROWS}x{COLS}_20semillas_{timestamp}.txt"

    lineas = [
        "============================================================",
        "CASO 3 — INFORME DE ROBUSTEZ (20 SEMILLAS)",
        "============================================================",
        f"Fecha: {timestamp}",
        f"Instancia: {ROWS}x{COLS} (48 variables)",
        f"Reads: {NUM_READS}, Sweeps: {NUM_SWEEPS}",
        f"Pesos QUBO: frontera={peso_frontera}, zona={peso_zona}, start_goal={peso_start_goal}",
        "",
        "RESUMEN AGREGADO:",
        f"  Fronteras mejor muestra: {np.mean(fronteras):.2f} ± {np.std(fronteras):.2f} (rango: [{min(fronteras)}, {max(fronteras)}])",
        f"  Tasa cumplimiento zonas: {np.mean(tasas_zonas):.2f}%",
        f"  Tasa muestras navegables: {np.mean(tasas_nav):.2f}%",
        f"  Semillas con mejor muestra navegable: {frac_mejores_navegables:.1f}%",
        f"  Tiempo medio: {np.mean(tiempos):.4f} s",
        "",
        "DETALLE POR SEMILLA:",
        "Semilla | Fronteras | Zonas_OK | Navegable | Comp | Long_BFS | Tasa_Nav | Tiempo(s)",
    ]

    for r in resultados_semillas:
        lineas.append(
            f"{r['seed']:7d} | {r['mejor_fronteras']:9d} | {str(r['mejor_zonas_ok']):8s} | "
            f"{str(r['mejor_navegable']):9s} | {r['mejor_componentes']:4d} | "
            f"{str(r['mejor_longitud_bfs']):8s} | {r['tasa_navegable']*100:7.1f}% | {r['tiempo']:.4f}"
        )

    archivo_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe guardado en: {archivo_txt}")

    return resultados_semillas, archivo_txt


if __name__ == "__main__":
    evaluar_robustez()
