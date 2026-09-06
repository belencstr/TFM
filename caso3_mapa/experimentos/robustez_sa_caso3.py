"""Evaluación de Robustez del QUBO Desacoplado (48 variables) a lo largo de 20 semillas.

Homogeneizado para comparativa directa con el QUBO Integrado:
- Mismas 20 semillas: [1000 + i * 37 for i in range(20)]
- Mismo número de lecturas: 100 reads
- Mismo número de sweeps: 1500 sweeps
- Misma penalización teórica a priori: P = 100.0 (> 82 aristas)
- Mide:
  * Tasa de éxito estricta: Zonas correctas + START/GOAL + Ruta navegable (BFS).
  * Time To Solution al 99% de confianza (TTS_99).
  * Fronteras de la mejor muestra válida vs. muestra de menor energía bruta.
  * Componentes conexas de suelo (métrica de calidad).
  * Tiempo medio de muestreo en CPU.
"""

from datetime import datetime
from pathlib import Path
import numpy as np
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import construir_qubo_geometria, ROWS, COLS, PENALIZACION_TEORICA_P
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

NUM_SEMILLAS = 20
SEMILLAS = [1000 + i * 37 for i in range(NUM_SEMILLAS)]
NUM_READS = 100
NUM_SWEEPS = 1500


def ejecutar_robustez_desacoplado(
    peso_frontera=1.0,
    peso_zona=PENALIZACION_TEORICA_P,
    peso_start_goal=PENALIZACION_TEORICA_P,
):
    print("=" * 70)
    print("CASO 3 — ROBUSTEZ DEL QUBO DESACOPLADO (48 VARIABLES, 20 SEMILLAS)")
    print(f"Configuración idéntica al Integrado: Reads={NUM_READS}, Sweeps={NUM_SWEEPS}, P={PENALIZACION_TEORICA_P}")
    print("=" * 70)

    qubo = construir_qubo_geometria(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
    )

    resultados = []

    for idx, seed in enumerate(SEMILLAS, 1):
        res = resolver_qubo_sa(
            qubo,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
            es_modelo_integrado=False,
        )

        valida = res["mejor_muestra_valida"]
        min_e = res["mejor_muestra_energia"]

        fronteras_val = valida["fronteras"] if valida else None
        comp_val = valida["componentes"] if valida else None
        fronteras_mine = min_e["fronteras"]

        tasa_zonas = sum(1 for m in res["muestras"] if m["zonas_ok"]) / float(len(res["muestras"]))
        tasa_nav = sum(1 for m in res["muestras"] if m["es_navegable_bfs"]) / float(len(res["muestras"]))

        resultados.append({
            "seed": seed,
            "tiempo": res["tiempo_segundos"],
            "p_exito": res["p_exito"],
            "tts_99": res["tts_99_segundos"],
            "tiene_valida": valida is not None,
            "fronteras_val": fronteras_val,
            "comp_val": comp_val,
            "fronteras_mine": fronteras_mine,
            "tasa_zonas": tasa_zonas,
            "tasa_nav": tasa_nav,
        })

        tts_str = f"{res['tts_99_segundos']*1000:6.2f} ms" if res["tts_99_segundos"] < float('inf') else "   inf   "
        f_val_str = f"{fronteras_val:2d}" if fronteras_val is not None else "N/A"
        c_val_str = f"{comp_val:2d}" if comp_val is not None else "N/A"

        print(
            f"[{idx:02d}/{NUM_SEMILLAS}] Semilla {seed:5d} | "
            f"P(éxito): {res['p_exito']*100:5.1f}% | "
            f"TTS_99: {tts_str} | "
            f"Fronteras_Val: {f_val_str} (Comp: {c_val_str}) | "
            f"Fronteras_MinE: {fronteras_mine:2d} | "
            f"Tiempo: {res['tiempo_segundos']:.3f} s"
        )

    # Agregados
    tiempos = [r["tiempo"] for r in resultados]
    p_exitos = [r["p_exito"] * 100 for r in resultados]
    tts_validos = [r["tts_99"] for r in resultados if r["tts_99"] < float('inf')]
    validas_fronteras = [r["fronteras_val"] for r in resultados if r["fronteras_val"] is not None]
    validas_comp = [r["comp_val"] for r in resultados if r["comp_val"] is not None]
    mine_fronteras = [r["fronteras_mine"] for r in resultados]
    tasa_semillas_con_valida = sum(1 for r in resultados if r["tiene_valida"]) / NUM_SEMILLAS * 100

    print()
    print("=" * 70)
    print("RESUMEN ESTADÍSTICO QUBO DESACOPLADO (20 SEMILLAS)")
    print("=" * 70)
    print(f"Tasa media de éxito (Zonas + START/GOAL + BFS): {np.mean(p_exitos):.2f}% ± {np.std(p_exitos):.2f}%")
    print(f"Semillas que encuentran al menos 1 solución válida: {tasa_semillas_con_valida:.1f}%")
    if validas_fronteras:
        print(f"Fronteras de la mejor solución válida: {np.mean(validas_fronteras):.2f} ± {np.std(validas_fronteras):.2f} (rango: [{min(validas_fronteras)}, {max(validas_fronteras)}])")
    print(f"Fronteras muestra menor energía bruta: {np.mean(mine_fronteras):.2f} ± {np.std(mine_fronteras):.2f}")
    if tts_validos:
        print(f"TTS_99 medio en CPU: {np.mean(tts_validos)*1000:.2f} ± {np.std(tts_validos)*1000:.2f} ms")
    print(f"Tiempo medio de muestreo por semilla: {np.mean(tiempos):.4f} s")
    print("=" * 70)

    # Guardar archivo consolidado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_txt = RESULTADOS_DIR / f"robustez_sa_desacoplado_48vars_20semillas_{timestamp}.txt"

    lineas = [
        "===========================================================================",
        "CASO 3 — ROBUSTEZ DEL QUBO DESACOPLADO (48 VARIABLES, 20 SEMILLAS)",
        "===========================================================================",
        f"Fecha: {timestamp}",
        f"Instancia: {ROWS}x{COLS} (48 celdas x, 48 variables binarias)",
        f"Términos cuadráticos: {qubo.get('num_terminos_cuadraticos', 278)}",
        f"Reads={NUM_READS}, Sweeps={NUM_SWEEPS}",
        f"Penalización a priori: P = {peso_zona} (> 82 aristas)",
        "",
        "RESUMEN AGREGADO:",
        f"  Tasa media de éxito (zonas + BFS navegable): {np.mean(p_exitos):.2f}% ± {np.std(p_exitos):.2f}%",
        f"  Semillas con solución válida: {tasa_semillas_con_valida:.1f}%",
        f"  Fronteras solución válida: {np.mean(validas_fronteras):.2f} ± {np.std(validas_fronteras):.2f} (rango: [{min(validas_fronteras) if validas_fronteras else 'N/A'}, {max(validas_fronteras) if validas_fronteras else 'N/A'}])",
        f"  Fronteras muestra mínima energía: {np.mean(mine_fronteras):.2f} ± {np.std(mine_fronteras):.2f}",
        f"  TTS_99 medio en CPU: {np.mean(tts_validos)*1000:.2f} ms (desv: {np.std(tts_validos)*1000:.2f} ms)",
        f"  Tiempo medio de muestreo: {np.mean(tiempos):.4f} s",
        "",
        "DETALLE POR SEMILLA:",
        "Semilla | P(éxito) | TTS_99 (s) | Fronteras_Val | Comp_Val | Fronteras_MinE | Tiempo (s)",
        "-" * 80,
    ]

    for r in resultados:
        tts_val = f"{r['tts_99']:.6f}" if r["tts_99"] < float('inf') else "      inf"
        f_val = f"{r['fronteras_val']:13d}" if r['fronteras_val'] is not None else "          N/A"
        c_val = f"{r['comp_val']:8d}" if r['comp_val'] is not None else "     N/A"
        lineas.append(
            f"{r['seed']:7d} | {r['p_exito']*100:7.1f}% | {tts_val} | "
            f"{f_val} | {c_val} | {r['fronteras_mine']:14d} | {r['tiempo']:.4f}"
        )

    archivo_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe guardado en: {archivo_txt}")

    return {
        "resultados": resultados,
        "p_exito_mean": np.mean(p_exitos),
        "p_exito_std": np.std(p_exitos),
        "tts_mean_ms": np.mean(tts_validos) * 1000 if tts_validos else float('inf'),
        "tts_std_ms": np.std(tts_validos) * 1000 if tts_validos else 0.0,
        "fronteras_val_mean": np.mean(validas_fronteras) if validas_fronteras else None,
        "fronteras_val_std": np.std(validas_fronteras) if validas_fronteras else None,
        "fronteras_mine_mean": np.mean(mine_fronteras),
        "fronteras_mine_std": np.std(mine_fronteras),
        "tiempo_mean": np.mean(tiempos),
        "archivo_txt": archivo_txt,
    }


if __name__ == "__main__":
    ejecutar_robustez_desacoplado()
