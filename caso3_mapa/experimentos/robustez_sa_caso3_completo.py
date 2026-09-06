"""Evaluación de Robustez Estadística del QUBO Completo (117 variables, 20 semillas).

Ejecuta exactamente el mismo protocolo experimental que los modelos desacoplado e integrado:
- 20 semillas pseudoaleatorias idénticas: [1000 + i * 37 for i in range(20)].
- 100 reads por semilla.
- 1500 sweeps por read.
- Penalización teórica a priori P = 100 > 82.

Mide rigurosamente:
1. Tasa de éxito estricta: % de reads que satisfacen simultáneamente el 100% de restricciones
   (balance zonal, START/GOAL, ruta q conexa, 2 enemigos, 2 recompensas, rama acoplada en dead-end).
2. Time To Solution al 99% de confianza (TTS_99) en CPU.
3. Fronteras reales de transición Ising en la mejor muestra válida.
4. Componentes conexas de suelo (métrica de calidad arquitectónica).
5. Comparativa directa de la progresión 48 -> 96 -> 117 variables.
"""

from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
import numpy as np
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import ROWS, COLS, START, GOAL
from formulacion.qubo_caso3_completo import construir_qubo_completo
from experimentos.ejecutar_sa_caso3_completo import (
    validar_nivel_completo,
    exportar_qubo_completo_blender,
)
from solvers.simulated_annealing_caso3 import (
    _importar_sampler,
    convertir_a_diccionario_qubo,
    extraer_mapa_de_solucion,
    contar_componentes,
    calcular_fronteras_reales,
    calcular_tts,
)

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

NUM_SEMILLAS = 20
SEMILLAS = [1000 + i * 37 for i in range(NUM_SEMILLAS)]
NUM_READS = 100
NUM_SWEEPS = 1500


def ejecutar_robustez_qubo_completo():
    print("=" * 78)
    print("CASO 3 — ROBUSTEZ DEL QUBO COMPLETO (117 VARIABLES, 20 SEMILLAS)")
    print("Geometría + Ruta + Gameplay (2 Enemigos + 1 Premio) + Rama Secundaria")
    print(f"Protocolo: {NUM_SEMILLAS} semillas × {NUM_READS} reads × {NUM_SWEEPS} sweeps | P=100")
    print("=" * 78)
    print()

    print("Construyendo matriz QUBO Completa de 117 variables...")
    t_q0 = perf_counter()
    qubo = construir_qubo_completo()
    Q = convertir_a_diccionario_qubo(qubo)
    t_qubo = perf_counter() - t_q0
    print(f"Matriz lista en {t_qubo:.3f} s: {qubo['num_vars']} variables, {len(qubo['cuadratico'])} acoplamientos.")
    print()

    SimulatedAnnealingSampler = _importar_sampler()
    sampler = SimulatedAnnealingSampler()

    resultados = []
    mejor_global = None

    print(f"Ejecutando muestreo estocástico sobre las {NUM_SEMILLAS} semillas...")
    for idx, seed in enumerate(SEMILLAS, 1):
        t0 = perf_counter()
        sampleset = sampler.sample_qubo(
            Q,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
        )
        tiempo_sa = perf_counter() - t0

        muestras_validas = []
        num_exito = 0

        for reg in sampleset.data(fields=["sample", "energy", "num_occurrences"], sorted_by="energy"):
            sol_dict = dict(reg.sample)
            energia_total = float(reg.energy) + qubo["constante"]
            open_cells = extraer_mapa_de_solucion(sol_dict)

            es_valido, g_info, motivo = validar_nivel_completo(sol_dict, open_cells)
            if es_valido:
                num_exito += int(reg.num_occurrences)
                comp = contar_componentes(open_cells)
                fronteras = calcular_fronteras_reales(open_cells)
                info = {
                    "energia": energia_total,
                    "open_cells": open_cells,
                    "gameplay_info": g_info,
                    "componentes": comp,
                    "fronteras": fronteras,
                    "seed": seed,
                }
                muestras_validas.append(info)

        p_exito = num_exito / float(NUM_READS)
        tts_99 = calcular_tts(tiempo_sa, NUM_READS, p_exito, confianza=0.99)
        valida = muestras_validas[0] if muestras_validas else None

        fronteras_val = valida["fronteras"] if valida else None
        comp_val = valida["componentes"] if valida else None
        patron_val = valida["gameplay_info"]["branch_pattern_id"] if valida else None

        if valida and (mejor_global is None or valida["fronteras"] < mejor_global["fronteras"]):
            mejor_global = valida

        resultados.append({
            "seed": seed,
            "tiempo": tiempo_sa,
            "p_exito": p_exito,
            "tts_99": tts_99,
            "tiene_valida": valida is not None,
            "fronteras_valida": fronteras_val,
            "componentes_valida": comp_val,
            "patron_rama": patron_val,
        })

        tts_str = f"{tts_99*1000:6.2f} ms" if tts_99 < float("inf") else "   inf   "
        print(
            f"[{idx:02d}/{NUM_SEMILLAS}] Semilla {seed:5d} | "
            f"P(éxito): {p_exito*100:5.1f}% | "
            f"TTS_99: {tts_str} | "
            f"Fronteras: {str(fronteras_val):>4s} | "
            f"Comp: {str(comp_val):>2s} | "
            f"Rama: #{str(patron_val):>2s} | "
            f"Tiempo: {tiempo_sa:.3f} s"
        )

    print()
    print("=" * 78)
    print("RESUMEN ESTADÍSTICO CONSOLIDADO — QUBO COMPLETO (20 SEMILLAS)")
    print("=" * 78)

    p_exitos = [r["p_exito"] * 100 for r in resultados]
    tiempos = [r["tiempo"] for r in resultados]
    tts_vals = [r["tts_99"] for r in resultados if r["tts_99"] < float("inf")]
    fronteras_list = [r["fronteras_valida"] for r in resultados if r["fronteras_valida"] is not None]
    comp_list = [r["componentes_valida"] for r in resultados if r["componentes_valida"] is not None]
    semillas_con_valida = sum(1 for r in resultados if r["tiene_valida"])

    p_mean, p_std = np.mean(p_exitos), np.std(p_exitos)
    t_mean, t_std = np.mean(tiempos), np.std(tiempos)
    f_mean, f_std = (np.mean(fronteras_list), np.std(fronteras_list)) if fronteras_list else (0, 0)

    if tts_vals:
        tts_mean_ms = np.mean(tts_vals) * 1000
        tts_std_ms = np.std(tts_vals) * 1000
        tts_str_resumen = f"{tts_mean_ms:.2f} ± {tts_std_ms:.2f} ms"
    else:
        tts_str_resumen = "inf"

    print(f"Semillas con ≥1 solución válida: {semillas_con_valida}/{NUM_SEMILLAS} ({semillas_con_valida/NUM_SEMILLAS*100:.1f}%)")
    print(f"Tasa de éxito media:             {p_mean:.2f} ± {p_std:.2f} %")
    print(f"Time To Solution (TTS_99) medio: {tts_str_resumen}")
    print(f"Fronteras en solución válida:    {f_mean:.2f} ± {f_std:.2f}")
    if comp_list:
        print(f"Componentes conexas de suelo:    Rango [{min(comp_list)}, {max(comp_list)}] (Media: {np.mean(comp_list):.2f})")
    print(f"Tiempo medio de muestreo:        {t_mean:.3f} ± {t_std:.3f} s por semilla")
    print()

    # Guardar resultados en JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTADOS_DIR / f"robustez_qubo_completo_20semillas_{timestamp}.json"
    data_to_save = {
        "num_semillas": NUM_SEMILLAS,
        "num_reads": NUM_READS,
        "num_sweeps": NUM_SWEEPS,
        "semillas": SEMILLAS,
        "resumen": {
            "p_exito_mean": p_mean,
            "p_exito_std": p_std,
            "tts_99_mean_ms": np.mean(tts_vals) * 1000 if tts_vals else None,
            "tts_99_std_ms": np.std(tts_vals) * 1000 if tts_vals else None,
            "fronteras_mean": f_mean,
            "fronteras_std": f_std,
            "semillas_con_valida": semillas_con_valida,
            "tiempo_mean_s": t_mean,
            "componentes_min": min(comp_list) if comp_list else None,
            "componentes_max": max(comp_list) if comp_list else None,
        },
        "detalles_por_semilla": resultados,
    }
    json_path.write_text(json.dumps(data_to_save, indent=2), encoding="utf-8")
    print(f"Resultados guardados en: {json_path}")
    print("=" * 78)
    print()

    # Imprimir la tabla de progresión 48 -> 96 -> 117
    print("TABLA DE PROGRESIÓN CONCEPTUAL DEL CASO 3 (20 SEMILLAS × 100 READS × 1500 SWEEPS):")
    print("-" * 88)
    print(f"{'Modelo':<20} | {'Vars':<5} | {'Qué incorpora':<35} | {'P(éxito)':<12} | {'TTS_99':<15} | {'Fronteras':<10}")
    print("-" * 88)
    print(f"{'QUBO desacoplado':<20} | {'48':<5} | {'Geometría Ising + BFS ext.':<35} | {'8.30 ± 2.51 %':<12} | {'63.47 ± 28.29 ms':<15} | {'34.55 ± 2.13':<10}")
    print(f"{'QUBO integrado':<20} | {'96':<5} | {'Geometría + Ruta START->GOAL':<35} | {'93.60 ± 2.35 %':<12} | {' 4.39 ±  0.69 ms':<15} | {'29.25 ± 2.14':<10}")
    print(f"{'QUBO Full':<20} | {'117':<5} | {'Geom + Ruta + Gameplay + Rama':<35} | {f'{p_mean:.2f} ± {p_std:.2f} %':<12} | {tts_str_resumen:<15} | {f'{f_mean:.2f} ± {f_std:.2f}':<10}")
    print("-" * 88)

    return data_to_save


if __name__ == "__main__":
    ejecutar_robustez_qubo_completo()
