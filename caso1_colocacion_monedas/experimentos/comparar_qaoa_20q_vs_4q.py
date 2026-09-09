"""Caso 1 — Comparativa Rigurosa: QAOA 20 Qubits (Directo) vs QAOA 4 Qubits (Compacto para k=2).

Este script genera la evidencia comparativa definitiva para la memoria del TFM:
1. Contrasta las métricas del experimento previo de 20 qubits con el nuevo de 4 qubits.
2. Explica analíticamente la influencia decisiva de la codificación en algoritmos variacionales.
3. Genera una figura gráfica académica pulida en figuras/ (comparativa_qaoa_20q_vs_4q.png) con:
   - Dimensión del espacio de Hilbert (escala log).
   - Probabilidad de muestreo por disparo para la configuración representativa (maxiter=25, shots=160).
   - Tiempo de simulación en las configuraciones de referencia registradas.
   - Time-to-Target 99% (TTS99 estimado sin barras ficticias para inf).
4. Guarda un informe textual exhaustivo en resultados/.
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


import json
from pathlib import Path


def generar_figura_comparativa(carpeta_figuras):
    os.makedirs(carpeta_figuras, exist_ok=True)
    ruta_figura = os.path.join(carpeta_figuras, "comparativa_qaoa_20q_vs_4q.png")

    ruta_20q = os.path.join(RAIZ, "resultados", "benchmark_qaoa_20q.json")
    ruta_4q = os.path.join(RAIZ, "resultados", "benchmark_qaoa_compacto_4q.json")

    if not os.path.exists(ruta_20q):
        raise FileNotFoundError(f"Registro congelado no encontrado: {ruta_20q}")
    if not os.path.exists(ruta_4q):
        raise FileNotFoundError(f"Registro congelado no encontrado: {ruta_4q}")

    with open(ruta_20q, "r", encoding="utf-8") as f:
        data_20q = json.load(f)
    with open(ruta_4q, "r", encoding="utf-8") as f:
        data_4q = json.load(f)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9.5))
    plt.subplots_adjust(hspace=0.40, wspace=0.32)

    metodos = ["QAOA Directo\n(20 qubits)", "QAOA Compacto\n(4 qubits, k=2)"]
    x = np.arange(len(metodos))
    ancho = 0.35

    # 1. Espacio de Hilbert (Escala Logarítmica)
    ax1 = axes[0, 0]
    estados_totales = [
        data_20q["espacio_hilbert"]["dimension_total"],
        data_4q["espacio_hilbert"]["dimension_total"],
    ]
    estados_factibles = [
        data_20q["espacio_hilbert"]["estados_factibles"],
        data_4q["espacio_hilbert"]["estados_factibles"],
    ]

    ax1.bar(x - ancho/2, estados_totales, ancho, label="Estados Totales ($2^N$)", color="#2c3e50")
    ax1.bar(x + ancho/2, estados_factibles, ancho, label="Estados Factibles", color="#27ae60")
    ax1.set_yscale("log")
    ax1.set_ylim(1, 1e7)
    ax1.set_ylabel("Número de estados (escala log)")
    ax1.set_title("Dimensión del Espacio de Hilbert", fontsize=11, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(metodos)
    ax1.legend(loc="upper right")
    ax1.grid(True, linestyle="--", alpha=0.4, which="both")

    pct_fact_20q = data_20q["espacio_hilbert"]["fraccion_factible_pct"]
    pct_fact_4q = data_4q["espacio_hilbert"]["fraccion_factible_pct"]
    ax1.text(0 + ancho/2, 160, f"{pct_fact_20q:.4f}%", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)
    ax1.text(1 + ancho/2, 10, f"{pct_fact_4q:.2f}%", ha="center", va="bottom", fontweight="bold", color="#1e8449", fontsize=9)

    # 2. Probabilidad de Muestreo (p / shot)
    ax2 = axes[0, 1]
    prob_factible = [
        data_20q["rendimiento_experimental"]["probabilidad_factible_pct"],
        data_4q["rendimiento_experimental"]["probabilidad_factible_pct"],
    ]
    prob_optimo = [
        data_20q["rendimiento_experimental"]["probabilidad_optimo_pct"],
        data_4q["rendimiento_experimental"]["probabilidad_optimo_pct"],
    ]

    ax2.bar(x - ancho/2, prob_factible, ancho, label="Prob. Factible (%)", color="#2980b9")
    ax2.bar(x + ancho/2, prob_optimo, ancho, label="Prob. Óptimo (%)", color="#8e44ad")
    ax2.set_ylabel("Probabilidad por disparo (%)")
    ax2.set_title("Probabilidad empírica observada por disparo\n(4Q: maxiter=25, shots=160; 20Q: 0% en el barrido evaluado)", fontsize=9.5, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(metodos)
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle="--", alpha=0.4)

    for i, (pf, po) in enumerate(zip(prob_factible, prob_optimo)):
        if pf > 0:
            ax2.text(i - ancho/2, pf + 2, f"{pf:.1f}%", ha="center", fontweight="bold", fontsize=9)
        else:
            ax2.text(i - ancho/2, 2, "0.0%", ha="center", fontweight="bold", color="#c0392b", fontsize=9)

        if po > 0:
            ax2.text(i + ancho/2, po + 2, f"{po:.1f}%", ha="center", fontweight="bold", fontsize=9)
        else:
            ax2.text(i + ancho/2, 2, "0.0%", ha="center", fontweight="bold", color="#c0392b", fontsize=9)

    # 3. Tiempo de Simulación Cuántica
    ax3 = axes[1, 0]
    tiempos = [
        data_20q["rendimiento_experimental"]["tiempo_simulacion_segundos"],
        data_4q["rendimiento_experimental"]["tiempo_simulacion_segundos"],
    ]
    colores_tiempo = ["#e74c3c", "#2ecc71"]
    ax3.bar(metodos, tiempos, color=colores_tiempo, width=0.45)
    ax3.set_yscale("log")
    ax3.set_ylim(0.05, 3000.0)
    ax3.set_ylabel("Tiempo de simulación en s (escala log)")
    ax3.set_title("Tiempo de Simulación (Configuración de Referencia)", fontsize=10, fontweight="bold")
    ax3.grid(True, linestyle="--", alpha=0.4, which="both")

    t20 = tiempos[0]
    t4 = tiempos[1]
    ax3.text(0, t20 * 1.3, f"{t20:.2f} s\n(~{t20/60:.1f} min)", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=9)
    ax3.text(1, t4 * 1.4, f"{t4:.3f} s\n(≈{t20/t4:.0f}× menor\ntiempo observado)", ha="center", va="bottom", fontweight="bold", color="#196f3d", fontsize=9)

    # 4. Time-to-Target 99% (TTS99 Estimado en Simulación)
    ax4 = axes[1, 1]
    tts_compacto = data_4q["rendimiento_experimental"]["tts_batch_99_segundos"]
    ax4.bar([1], [tts_compacto], color=["#16a085"], width=0.45)
    ax4.set_xlim(-0.6, 1.6)
    ax4.set_ylim(0.01, 2.0)
    ax4.set_yscale("log")
    ax4.set_ylabel("TTS_batch_99 estimado en segundos (escala log)")
    ax4.set_title("Time-to-Target 99% — Configuración de Referencia", fontsize=10.5, fontweight="bold")
    ax4.set_xticks([0, 1])
    ax4.set_xticklabels(metodos)
    ax4.grid(True, linestyle="--", alpha=0.4, which="both")

    ax4.text(
        0, 0.15,
        "No estimable\n($p_{\\mathrm{opt}}=0$)",
        ha="center", va="center",
        color="#c0392b", fontweight="bold", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fceae8", ec="#e74c3c", lw=1.2)
    )
    tts_min_barrido = data_4q["barrido"]["tts_batch_99_min_segundos"]
    tts_max_barrido = data_4q["barrido"]["tts_batch_99_max_segundos"]
    ax4.text(
        1, tts_compacto * 1.35,
        f"{tts_compacto:.2f} s ($TTS_{{\\mathrm{{batch}},99}}$)\nBarrido: {tts_min_barrido:.4f}–{tts_max_barrido:.4f} s",
        ha="center", va="bottom",
        color="#0e6251", fontweight="bold", fontsize=8.5
    )

    plt.suptitle("Caso 1: Influencia de la Codificación Cuántica en QAOA (20 Qubits vs 4 Qubits)", fontsize=13, fontweight="bold")
    plt.savefig(ruta_figura, dpi=300, bbox_inches="tight")
    plt.close()
    return ruta_figura


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    carpeta_figuras = os.path.join(RAIZ, "figuras")
    os.makedirs(carpeta_resultados, exist_ok=True)
    os.makedirs(carpeta_figuras, exist_ok=True)

    ruta_20q = os.path.join(RAIZ, "resultados", "benchmark_qaoa_20q.json")
    ruta_4q = os.path.join(RAIZ, "resultados", "benchmark_qaoa_compacto_4q.json")

    if not os.path.exists(ruta_20q):
        raise FileNotFoundError(f"Registro congelado no encontrado: {ruta_20q}")
    if not os.path.exists(ruta_4q):
        raise FileNotFoundError(f"Registro congelado no encontrado: {ruta_4q}")

    with open(ruta_20q, "r", encoding="utf-8") as f:
        data_20q = json.load(f)
    with open(ruta_4q, "r", encoding="utf-8") as f:
        data_4q = json.load(f)

    ruta_figura = generar_figura_comparativa(carpeta_figuras)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(carpeta_resultados, f"comparativa_qaoa_20q_vs_4q_{marca}.txt")

    # Extracción estricta sin fallbacks
    cfg_20 = data_20q["configuracion"]
    cfg_4 = data_4q["configuracion"]
    hilbert_20 = data_20q["espacio_hilbert"]
    hilbert_4 = data_4q["espacio_hilbert"]
    rend_20 = data_20q["rendimiento_experimental"]
    rend_4 = data_4q["rendimiento_experimental"]
    barrido_4 = data_4q["barrido"]

    qubits_20 = cfg_20["qubits"]
    qubits_4 = cfg_4["qubits"]
    dim_20 = hilbert_20["dimension_total"]
    dim_4 = hilbert_4["dimension_total"]
    fact_20 = hilbert_20["estados_factibles"]
    fact_4 = hilbert_4["estados_factibles"]
    pct_fact_20 = hilbert_20["fraccion_factible_pct"]
    pct_fact_4 = hilbert_4["fraccion_factible_pct"]
    opt_20 = hilbert_20["estados_optimos"]
    opt_4 = hilbert_4["estados_optimos"]
    pct_opt_20 = hilbert_20["fraccion_optima_pct"]
    pct_opt_4 = hilbert_4["fraccion_optima_pct"]

    t_sim_20 = rend_20["tiempo_simulacion_segundos"]
    t_sim_4 = rend_4["tiempo_simulacion_segundos"]
    p_fact_20 = rend_20["probabilidad_factible_pct"]
    p_fact_4 = rend_4["probabilidad_factible_pct"]
    p_opt_20 = rend_20["probabilidad_optimo_pct"]
    p_opt_4 = rend_4["probabilidad_optimo_pct"]

    cota_rejilla = rend_20["cota_rejilla_analitica"]
    p_fact_cota = cota_rejilla["p_fact_max_rejilla_pct"]
    p_opt_cota = cota_rejilla["p_opt_max_rejilla_pct"]

    # Cálculo dinámico de probabilidades de 0 éxitos en N disparos: P(0) = (1 - p)^N
    p_fact_elem = p_fact_cota / 100.0
    p_opt_elem = p_opt_cota / 100.0

    p0_fact_20 = ((1.0 - p_fact_elem) ** 20) * 100.0
    p0_opt_20 = ((1.0 - p_opt_elem) ** 20) * 100.0

    p0_fact_160 = ((1.0 - p_fact_elem) ** 160) * 100.0
    p0_opt_160 = ((1.0 - p_opt_elem) ** 160) * 100.0

    p0_fact_2048 = ((1.0 - p_fact_elem) ** 2048) * 100.0
    p0_opt_2048 = ((1.0 - p_opt_elem) ** 2048) * 100.0

    tts_str_20 = "No estimable (p_opt=0)" if not rend_20["tts_estimable"] else f"{rend_20['tts_segundos']:.4f} s"
    tts_min_4 = barrido_4["tts_batch_99_min_segundos"]
    tts_max_4 = barrido_4["tts_batch_99_max_segundos"]
    tts_str_4 = f"{tts_min_4:.4f} s - {tts_max_4:.4f} s"

    sol_bits_4 = rend_4["solucion_bits"]
    coste_4 = rend_4["coste_pmedian"]

    factor_qubits = f"-{(1.0 - qubits_4 / qubits_20) * 100:.1f}%"
    factor_dim = f"{dim_20 // dim_4:,}x menor"
    factor_fact = f"≈{pct_fact_4 / pct_fact_20:.0f}× mayor"
    factor_opt = f"≈{pct_opt_4 / pct_opt_20:.0f}× mayor"
    factor_tiempo = f"≈{t_sim_20 / t_sim_4:.0f}× menor tiempo"

    informe = f"""========================================================================================
CASO 1 — INFORME COMPARATIVO: QAOA {qubits_20} QUBITS (DIRECTO) VS {qubits_4} QUBITS (COMPACTO PARA k={cfg_4['k']})
========================================================================================
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Problema: Colocación de Monedas (p-median, instancia mínima con k={cfg_4['k']} sobre {cfg_4['n_candidatas']} candidatas)
Fuente 20Q: {os.path.basename(ruta_20q)} (congelado {data_20q['fecha_congelacion']})
Fuente 4Q:  {os.path.basename(ruta_4q)} (congelado {data_4q['fecha_congelacion']})

1. SÍNTESIS DEL PROBLEMA Y CONTEXTO
En el Caso 1, el problema de colocación de monedas se modela originalmente como p-median /
k-medoids. Para las instancias de mapa completo se utiliza k=4. Como estudio de la
viabilidad de resolución cuántica variacional (QAOA), se planteó una instancia mínima
con n={cfg_4['n_candidatas']} candidatas y k={cfg_4['k']} monedas.

La primera formulación tradujo directamente el modelo lineal estándar de enteros (PLI)
utilizando variables de apertura x_j ({cfg_20['variables_x']}) y variables de asignación y_ij ({cfg_20['variables_y']}):
    N = n + n^2 = {cfg_20['variables_x']} + {cfg_20['variables_y']} = {qubits_20} variables binarias -> {qubits_20} QUBITS.

En el barrido sistemático del modelo directo ({rend_20['motivo_fallo']}), esta codificación arrojó:
    - Probabilidad factible observada: {p_fact_20:.2f}%
    - Probabilidad óptima observada:   {p_opt_20:.2f}%
    - TTS99: {tts_str_20} por ausencia de éxitos (p_opt = 0).

2. DIAGNÓSTICO EXPERIMENTAL Y ANALÍTICO
a) Representación del subespacio factible:
   - El espacio de Hilbert con {qubits_20} qubits comprende 2^{qubits_20} = {dim_20:,} estados.
   - Únicamente {fact_20} estados ({pct_fact_20:.4f}%) satisfacen simultáneamente la cardinalidad
     y las restricciones de asignación y enlace.
   - Únicamente {opt_20} estados ({pct_opt_20:.5f}%) representan soluciones óptimas globales.
b) Evaluación unitaria exacta de QAOA con mezclador estándar (p={cfg_20['reps_p']}):
   - Mediante simulación analítica de la evolución unitaria completa
     (script reproducible: experimentos/simulacion_unitaria_20q_max_prob.py),
     se evaluó una rejilla de 225 puntos en el plano de parámetros variacionales (gamma, beta).
   - En la rejilla evaluada, la probabilidad de medir un estado factible alcanza como máximo
     un ~{p_fact_cota:.4f}% (p_fact = {p_fact_cota/100:.6f}), y la de medir un estado óptimo un ~{p_opt_cota:.4f}% (p_opt = {p_opt_cota/100:.6f}).
   - Con esa probabilidad, la probabilidad de observar cero éxitos P(0) = (1 - p)^N calculada analíticamente es:
     * Con N = 20 shots:  {p0_fact_20:.2f}% sin factibles, {p0_opt_20:.2f}% sin óptimos.
     * Con N = 160 shots: {p0_fact_160:.2f}% sin factibles, {p0_opt_160:.2f}% sin óptimos.
     * Con N = 2048 shots: {p0_fact_2048:.2f}% sin factibles, {p0_opt_2048:.2f}% sin óptimos.
   - Por tanto, en el barrido sistemático con 20 a 160 disparos, no observar ninguna muestra
     factible u óptima es estadísticamente esperable ({p0_fact_160:.1f}% a {p0_opt_20:.1f}% de probabilidad de ausencia).
     Con 2048 disparos, no observar óptimos sigue siendo la norma (~{p0_opt_2048:.1f}%), mientras que la ausencia de factibles
     refleja adicionalmente que el optimizador clásico (COBYLA a p=1) no converge necesariamente al parámetro óptimo de la rejilla.
c) Conclusión de esta fase:
   En esta codificación directa, con p=1, el mezclador transversal estándar y la
   configuración evaluada, el subespacio factible resulta extremadamente poco representado
   y QAOA no produjo muestras factibles en los experimentos realizados.

3. LA REFORMULACIÓN COMPACTA ESPECÍFICA PARA k={cfg_4['k']}
En lugar de desechar QAOA, este resultado negativo motivó una revisión de la codificación:
Para el caso particular de k=2 monedas, cualquier selección factible contiene exactamente
un único par de centros activo (x_j x_l = 1). Por tanto, el coste de asignación óptimo de
cada pareja puede precalcularse analíticamente como:
    C(j, l) = sum_i min(d_ij, d_il)
permitiendo formular el problema de forma exacta mediante una forma cuadrática pura
sobre únicamente las n variables de decisión x_j:
    H(x) = sum_{{j < l}} C(j, l) x_j x_l + A (sum_j x_j - {cfg_4['k']})^2

(Nota de alcance: esta propiedad es específica de k=2; para k > 2 habría C(k,2) productos
cruzados activos y la suma de parejas no reproduce min_{{j in S}} d_ij).

Para fijar la penalización A sin utilizar el óptimo (el cual no se conoce a priori en un
caso real), se utiliza la solución factible conocida obtenida mediante PAM (cota_factible),
reservando la búsqueda exhaustiva exclusivamente para la evaluación posterior de las muestras.

4. TABLA COMPARATIVA DIRECTA (GENERADA DESDE REGISTROS CONGELADOS)
----------------------------------------------------------------------------------------
Métrica                        | QAOA Directo ({qubits_20} Qubits) | QAOA Compacto ({qubits_4} Qubits, k={cfg_4['k']}) | Factor de Mejora
-------------------------------+--------------------------+-------------------------------+-----------------
Qubits                         | {qubits_20} qubits                | {qubits_4} qubits                      | {factor_qubits}
Dimensión espacio Hilbert      | {dim_20:,} estados        | {dim_4} estados                    | {factor_dim}
Fracción de estados factibles  | {pct_fact_20:.4f}% ({fact_20} estados)     | {pct_fact_4:.2f}% ({fact_4} estados)            | {factor_fact}
Fracción de estados óptimos    | {pct_opt_20:.5f}% ({opt_20} estados)     | {pct_opt_4:.2f}% ({opt_4} estados)            | {factor_opt}
Tiempo simulación (config. ref.) | {t_sim_20:.2f} s (iter={cfg_20['cobyla_maxiter']:<2})       | {t_sim_4:.4f} s (iter={cfg_4['cobyla_maxiter']:<2})         | {factor_tiempo}
Prob. factible observada       | {p_fact_20:.2f}%                    | {p_fact_4:.2f}%                       | Muestras factibles
Prob. óptima observada         | {p_opt_20:.2f}%                    | {p_opt_4:.2f}%                       | Muestras óptimas
TTS99 estimado (simulación)    | {tts_str_20:<24} | {tts_str_4:<29} | Estimación finita
Solución devuelta              | Inviable (0% factible)   | {sol_bits_4} (Coste = {coste_4})      | Óptimo exacto
Escalabilidad analítica (k=2)  | n + n^2 variables binarias | n variables binarias          | Formulación compacta
----------------------------------------------------------------------------------------

Notas metodológicas sobre tiempos y reproducibilidad:
1. Simulación clásica (REPS = 1): Los tiempos de simulación y las estimaciones TTS corresponden
   al coste empírico de ejecución en CPU clásica (COBYLA + muestreo) con una repetición por configuración,
   por lo que no constituyen medidas de tiempo de hardware cuántico real (QPU).
2. Overhead de entorno: La primera ejecución presenta un tiempo superior a las posteriores, compatible
   con costes de inicialización o calentamiento del entorno de simulación. Esta medición no descompone
   dicho overhead por componentes.
3. Estimación condicionada de TTS_batch_99: Representa una estimación condicionada a la distribución
   obtenida tras la optimización, donde P_batch = 1 - (1 - p_shot)^S se infiere de la probabilidad por disparo.

5. APORTE CONCEPTUAL PARA LA MEMORIA DEL TFM
El contraste entre ambos enfoques no reemplaza el modelo general del Caso 1, sino que
aporta una contribución metodológica relevante:
"El primer resultado negativo nos llevó a revisar no el algoritmo, sino la formulación.
Al eliminar variables auxiliares que forman parte de la formulación lineal clásica pero
incrementan considerablemente el número de variables binarias en la codificación cuántica,
la misma instancia pasó de 20 a 4 qubits y QAOA sí produjo soluciones factibles y óptimas
con alta probabilidad. Por tanto, la elección de la codificación condiciona de forma
decisiva la viabilidad práctica de los algoritmos cuánticos variacionales."

Figura generada: {ruta_figura}
"""
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(informe)

    print(informe)
    print(f"Informe guardado en: {ruta_txt}")
    print(f"Figura guardada en:  {ruta_figura}")


if __name__ == "__main__":
    main()
