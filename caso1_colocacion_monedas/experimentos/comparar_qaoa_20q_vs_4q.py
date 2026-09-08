"""Caso 1 — Comparativa Rigurosa: QAOA 20 Qubits (Directo) vs QAOA 4 Qubits (Compacto para k=2).

Este script genera la evidencia comparativa definitiva para la memoria del TFM:
1. Contrasta las métricas del experimento previo de 20 qubits con el nuevo de 4 qubits.
2. Explica analíticamente la influencia decisiva de la codificación en algoritmos variacionales.
3. Genera una figura gráfica académica pulida en figuras/ (comparativa_qaoa_20q_vs_4q.png) con:
   - Dimensión del espacio de Hilbert (escala log).
   - Probabilidad de muestreo por disparo para la configuración representativa (maxiter=25, shots=160).
   - Tiempo de simulación con COBYLA (30 iter).
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


def generar_figura_comparativa(carpeta_figuras):
    os.makedirs(carpeta_figuras, exist_ok=True)
    ruta_figura = os.path.join(carpeta_figuras, "comparativa_qaoa_20q_vs_4q.png")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9.5))
    plt.subplots_adjust(hspace=0.40, wspace=0.32)

    metodos = ["QAOA Directo\n(20 qubits)", "QAOA Compacto\n(4 qubits, k=2)"]
    x = np.arange(len(metodos))
    ancho = 0.35

    # 1. Espacio de Hilbert (Escala Logarítmica)
    ax1 = axes[0, 0]
    estados_totales = [2**20, 2**4]
    estados_factibles = [96, 6]

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

    ax1.text(0 + ancho/2, 160, "0.0092%", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)
    ax1.text(1 + ancho/2, 10, "37.50%", ha="center", va="bottom", fontweight="bold", color="#1e8449", fontsize=9)

    # 2. Probabilidad de Muestreo (p / shot)
    ax2 = axes[0, 1]
    prob_factible = [0.0, 68.125]
    prob_optimo = [0.0, 65.625]

    ax2.bar(x - ancho/2, prob_factible, ancho, label="Prob. Factible (%)", color="#2980b9")
    ax2.bar(x + ancho/2, prob_optimo, ancho, label="Prob. Óptimo (%)", color="#8e44ad")
    ax2.set_ylabel("Probabilidad por disparo (%)")
    ax2.set_title("Probabilidad empírica observada por disparo\n(Configuración: maxiter = 25, shots = 160)", fontsize=10, fontweight="bold")
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
    tiempos = [513.69, 0.2872]
    colores_tiempo = ["#e74c3c", "#2ecc71"]
    ax3.bar(metodos, tiempos, color=colores_tiempo, width=0.45)
    ax3.set_yscale("log")
    ax3.set_ylim(0.05, 3000.0)
    ax3.set_ylabel("Tiempo de simulación en s (escala log)")
    ax3.set_title("Tiempo de Simulación (COBYLA 30 iter)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle="--", alpha=0.4, which="both")

    # Etiquetas con margen suficiente para evitar solapamientos
    ax3.text(0, 680.0, "513.69 s\n(~8.6 min)", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=9)
    ax3.text(1, 0.40, "0.287 s\n(>1780x más rápido)", ha="center", va="bottom", fontweight="bold", color="#196f3d", fontsize=9)

    # 4. Time-to-Target 99% (TTS99 Estimado)
    ax4 = axes[1, 1]
    # Rigor académico: En 20 qubits no dibujamos barra (es no estimable / inf)
    tts_compacto = 0.2872
    ax4.bar([1], [tts_compacto], color=["#16a085"], width=0.45)
    ax4.set_xlim(-0.6, 1.6)
    ax4.set_ylim(0.01, 2.0)
    ax4.set_yscale("log")
    ax4.set_ylabel("TTS99 estimado en segundos (escala log)")
    ax4.set_title("Time-to-Target 99% ($TTS_{99}$ estimado)", fontsize=11, fontweight="bold")
    ax4.set_xticks([0, 1])
    ax4.set_xticklabels(metodos)
    ax4.grid(True, linestyle="--", alpha=0.4, which="both")

    # Texto claro para 20 qubits indicando que es no estimable
    ax4.text(
        0, 0.15,
        "No estimable\n($p_{\\mathrm{opt}}=0$)",
        ha="center", va="center",
        color="#c0392b", fontweight="bold", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="#fceae8", ec="#e74c3c", lw=1.2)
    )
    ax4.text(
        1, tts_compacto * 1.5,
        f"{tts_compacto:.2f} s\n$TTS_{{99}}$ estimado",
        ha="center", va="bottom",
        color="#0e6251", fontweight="bold", fontsize=9
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

    ruta_figura = generar_figura_comparativa(carpeta_figuras)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(carpeta_resultados, f"comparativa_qaoa_20q_vs_4q_{marca}.txt")

    informe = f"""========================================================================================
CASO 1 — INFORME COMPARATIVO: QAOA 20 QUBITS (DIRECTO) VS 4 QUBITS (COMPACTO PARA k=2)
========================================================================================
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Problema: Colocación de Monedas (p-median, instancia mínima con k=2 sobre 4 candidatas)

1. SÍNTESIS DEL PROBLEMA Y CONTEXTO
En el Caso 1, el problema de colocación de monedas se modela originalmente como p-median /
k-medoids. Para las instancias de mapa completo se utiliza k=4. Como estudio de la
viabilidad de resolución cuántica variacional (QAOA), se planteó una instancia mínima
con n=4 candidatas y k=2 monedas.

La primera formulación tradujo directamente el modelo lineal estándar de enteros (PLI)
utilizando variables de apertura x_j (4) y variables de asignación y_ij (16):
    N = n + n^2 = 4 + 16 = 20 variables binarias -> 20 QUBITS.

En las 32 configuraciones del barrido sistemático (qaoa_tts_barrido.py: iter in [1..30],
shots in [20..160]), esta codificación directa arrojó:
    - Probabilidad factible observada: 0.00%
    - Probabilidad óptima observada:   0.00%
    - TTS99: No estimable por ausencia de éxitos (p_opt = 0).

2. DIAGNÓSTICO EXPERIMENTAL Y ANALÍTICO
a) Representación del subespacio factible:
   - El espacio de Hilbert con 20 qubits comprende 2^20 = 1.048.576 estados.
   - Únicamente 96 estados (0.0092%) satisfacen simultáneamente la cardinalidad
     y las restricciones de asignación y enlace.
   - Únicamente 6 estados (0.00057%) representan soluciones óptimas globales.
b) Evaluación unitaria exacta de QAOA con mezclador estándar (p=1):
   - Mediante simulación analítica de la evolución unitaria completa
     (script reproducible: experimentos/simulacion_unitaria_20q_max_prob.py),
     se evaluó una rejilla de 225 puntos en el plano de parámetros variacionales (gamma, beta).
   - En la rejilla evaluada, la probabilidad de medir un estado factible alcanza como máximo
     un ~0.0769% (p_fact = 0.000769), y la de medir un estado óptimo un ~0.0099% (p_opt = 0.000099).
   - Con esa probabilidad, la probabilidad de observar cero éxitos P(0) = (1 - p)^N es:
     * Con N = 20 shots:  98.47% sin factibles, 99.80% sin óptimos.
     * Con N = 160 shots: 88.42% sin factibles, 98.43% sin óptimos.
     * Con N = 2048 shots: 20.69% sin factibles, 81.71% sin óptimos.
   - Por tanto, en el barrido sistemático con 20 a 160 disparos, no observar ninguna muestra
     factible u óptima es estadísticamente muy plausible (88.4% a 99.8%). Con 2048 disparos,
     no observar óptimos sigue siendo la norma (~81.7%), mientras que la ausencia de factibles
     refleja adicionalmente que el optimizador clásico (COBYLA a p=1) no converge necesariamente
     al parámetro óptimo de la rejilla.
c) Conclusión de esta fase:
   En esta codificación directa, con p=1, el mezclador transversal estándar y la
   configuración evaluada, el subespacio factible resulta extremadamente poco representado
   y QAOA no produjo muestras factibles en los experimentos realizados.

3. LA REFORMULACIÓN COMPACTA ESPECÍFICA PARA k=2
En lugar de desechar QAOA, este resultado negativo motivó una revisión de la codificación:
Para el caso particular de k=2 monedas, cualquier selección factible contiene exactamente
un único par de centros activo (x_j x_l = 1). Por tanto, el coste de asignación óptimo de
cada pareja puede precalcularse analíticamente como:
    C(j, l) = sum_i min(d_ij, d_il)
permitiendo formular el problema de forma exacta mediante una forma cuadrática pura
sobre únicamente las n variables de decisión x_j:
    H(x) = sum_{{j < l}} C(j, l) x_j x_l + A (sum_j x_j - 2)^2

(Nota de alcance: esta propiedad es específica de k=2; para k > 2 habría C(k,2) productos
cruzados activos y la suma de parejas no reproduce min_{{j in S}} d_ij).

Para fijar la penalización A sin utilizar el óptimo (el cual no se conoce a priori en un
caso real), se utiliza la solución factible conocida obtenida mediante PAM (cota_factible),
reservando la búsqueda exhaustiva exclusivamente para la evaluación posterior de las muestras.

4. TABLA COMPARATIVA DIRECTA
----------------------------------------------------------------------------------------
Métrica                        | QAOA Directo (20 Qubits) | QAOA Compacto (4 Qubits, k=2) | Factor de Mejora
-------------------------------+--------------------------+-------------------------------+-----------------
Qubits                         | 20 qubits                | 4 qubits                      | -80.0%
Dimensión espacio Hilbert      | 1.048.576 estados        | 16 estados                    | 65.536x menor
Fracción de estados factibles  | 0.0092% (96 estados)     | 37.50% (6 estados)            | > 4.000x mayor
Fracción de estados óptimos    | 0.00057% (6 estados)     | 25.00% (4 estados)            | > 43.000x mayor
Tiempo simulación (30 iter)    | 513.69 segundos          | 0.2872 segundos               | > 1.780x más rápido
Prob. factible (maxiter=25)    | 0.00%                    | 68.13% (hasta 90.0% con N=20) | Muestras factibles
Prob. óptima (maxiter=25)      | 0.00%                    | 65.63% (hasta 85.0% con N=20) | Muestras óptimas
TTS99 estimado                 | No estimable (p_opt=0)   | 0.0087 s - 0.2872 s           | Estimación finita
Solución devuelta              | Inviable (0% factible)   | [0, 1, 0, 1] (Coste = 2)      | Óptimo exacto
Escalabilidad en qubits (k=2)  | n=8 -> 72 qubits         | n=8 -> 8 qubits (~0.85 s)     | Mejor escalabilidad
----------------------------------------------------------------------------------------

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
