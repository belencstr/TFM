"""Evaluación de Robustez del QUBO Integrado (96 variables) a lo largo de 20 semillas.

Mide rigurosamente:
- Tasa de éxito estricta: Cumplimiento de zonas + START/GOAL + Ruta q válida sobre suelo.
- Time To Solution al 99% de confianza (TTS_99).
- Fronteras de la mejor solución válida (coherencia espacial tipo Ising).
- Componentes conexas de suelo (métrica de calidad).
- Tiempo de ejecución y estabilidad estocástica.
"""

from datetime import datetime
from pathlib import Path
import numpy as np
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3_integrado import construir_qubo_integrado
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

NUM_SEMILLAS = 20
SEMILLAS = [1000 + i * 37 for i in range(NUM_SEMILLAS)]
NUM_READS = 100
NUM_SWEEPS = 1500


def ejecutar_robustez_integrado():
    print("=" * 70)
    print("CASO 3 — ROBUSTEZ DEL QUBO INTEGRADO (96 VARIABLES, 20 SEMILLAS)")
    print("Penalización teórica a priori P=100 > 82")
    print("=" * 70)

    qubo = construir_qubo_integrado()

    resultados = []

    for idx, seed in enumerate(SEMILLAS, 1):
        res = resolver_qubo_sa(
            qubo,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
            es_modelo_integrado=True,
        )

        valida = res["mejor_muestra_valida"]
        fronteras_val = valida["fronteras"] if valida else None
        comp_val = valida["componentes"] if valida else None

        resultados.append({
            "seed": seed,
            "tiempo": res["tiempo_segundos"],
            "p_exito": res["p_exito"],
            "tts_99": res["tts_99_segundos"],
            "tiene_valida": valida is not None,
            "fronteras_valida": fronteras_val,
            "componentes_valida": comp_val,
            "fronteras_energia": res["mejor_muestra_energia"]["fronteras"],
        })

        tts_str = f"{res['tts_99_segundos']*1000:6.2f} ms" if res["tts_99_segundos"] < float("inf") else "inf"
        print(
            f"[{idx:02d}/{NUM_SEMILLAS}] Semilla {seed:5d} | "
            f"P(éxito): {res['p_exito']*100:5.1f}% | "
            f"TTS_99: {tts_str} | "
            f"Fronteras Val: {str(fronteras_val):>4s} | "
            f"Comp: {str(comp_val):>3s} | "
            f"Tiempo: {res['tiempo_segundos']:.3f} s"
        )

    # Métricas agregadas
    p_exitos = [r["p_exito"] * 100 for r in resultados]
    tiempos = [r["tiempo"] for r in resultados]
    tts_vals = [r["tts_99"] for r in resultados if r["tts_99"] < float("inf")]
    fronteras_list = [r["fronteras_valida"] for r in resultados if r["fronteras_valida"] is not None]
    frac_semillas_con_valida = sum(1 for r in resultados if r["tiene_valida"]) / NUM_SEMILLAS * 100

    print()
    print("=" * 70)
    print("RESUMEN ESTADÍSTICO DEL QUBO INTEGRADO (20 SEMILLAS)")
    print("=" * 70)
    print(f"Tasa media de éxito (ruta q válida + zonas): {np.mean(p_exitos):.1f}% ± {np.std(p_exitos):.1f}%")
    print(f"Semillas que encuentran solución válida: {frac_semillas_con_valida:.1f}%")
    print(f"Fronteras de la mejor solución válida: {np.mean(fronteras_list):.2f} ± {np.std(fronteras_list):.2f} (min={min(fronteras_list)}, max={max(fronteras_list)})")
    if tts_vals:
        print(f"TTS_99 medio: {np.mean(tts_vals)*1000:.2f} ms ± {np.std(tts_vals)*1000:.2f} ms")
    print(f"Tiempo medio por semilla: {np.mean(tiempos):.4f} s (Total: {sum(tiempos):.2f} s)")
    print("=" * 70)

    # Guardar informe
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_txt = RESULTADOS_DIR / f"robustez_sa_integrado_96vars_20semillas_{timestamp}.txt"

    lineas = [
        "===========================================================================",
        "CASO 3 — ROBUSTEZ DEL QUBO INTEGRADO (96 VARIABLES, 20 SEMILLAS)",
        "===========================================================================",
        f"Fecha: {timestamp}",
        f"Instancia: 6x8 (48 celdas x, 48 pasos q = 96 variables binarias)",
        f"Términos cuadráticos: {len(qubo['cuadratico'])}",
        f"Reads={NUM_READS}, Sweeps={NUM_SWEEPS}",
        f"Penalización a priori: P = {qubo['params']['peso_zona']} (> 82 aristas)",
        "",
        "RESUMEN AGREGADO:",
        f"  Tasa media de éxito (ruta q válida + zonas): {np.mean(p_exitos):.2f}% ± {np.std(p_exitos):.2f}%",
        f"  Semillas con solución válida: {frac_semillas_con_valida:.1f}%",
        f"  Fronteras solución válida: {np.mean(fronteras_list):.2f} ± {np.std(fronteras_list):.2f} (rango: [{min(fronteras_list)}, {max(fronteras_list)}])",
        f"  TTS_99 medio: {np.mean(tts_vals):.6f} s ({np.mean(tts_vals)*1000:.2f} ms)",
        f"  Tiempo medio de muestreo: {np.mean(tiempos):.4f} s",
        "",
        "DETALLE POR SEMILLA:",
        "Semilla | P(éxito) | TTS_99 (s) | Fronteras_Val | Comp_Val | Fronteras_MinE | Tiempo (s)",
        "-" * 80,
    ]

    for r in resultados:
        f_val = str(r["fronteras_valida"]) if r["fronteras_valida"] is not None else "N/A"
        c_val = str(r["componentes_valida"]) if r["componentes_valida"] is not None else "N/A"
        lineas.append(
            f"{r['seed']:7d} | {r['p_exito']*100:7.1f}% | {r['tts_99']:10.6f} | {f_val:>13s} | "
            f"{c_val:>8s} | {r['fronteras_energia']:14d} | {r['tiempo']:.4f}"
        )

    archivo_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe guardado en: {archivo_txt}")

    return resultados, archivo_txt


if __name__ == "__main__":
    ejecutar_robustez_integrado()
