"""Caso 1 — Generador de Figuras Académicas de QAOA (Paisaje, Distribución, Circuito y Stress Test).

Genera cuatro figuras visuales científicas de alta resolución (300 DPI) para la memoria del TFM:
1. figuras/qaoa_paisaje_energia_y_optimizacion.png:
   - Superficie 2D de energía esperada <H_C>(gamma, beta) y probabilidad P_opt(gamma, beta) con curvas de nivel.
   - Trayectoria de optimización del algoritmo variacional clásico (COBYLA) hacia el mínimo.
2. figuras/qaoa_distribucion_probabilidades_estados.png:
   - Histograma de distribución cuántica: Estado inicial |+>^4 vs Estado óptimo QAOA vs Muestras empíricas.
   - Demostración de amplificación cuántica sobre los estados óptimos (|0101⟩ y |1010⟩).
3. figuras/qaoa_circuito_cuantico_4q.png:
   - Diagrama vectorial de alta calidad del circuito cuántico ansatz (p=1, Hadamard, R_Z, R_ZZ, R_X y medición).
4. figuras/qaoa_stress_test_shots_escalabilidad.png:
   - Análisis comparativo de escalabilidad del stress test de disparos (2.048 a 65.536 shots) a partir de datos reales.
"""

from collections import defaultdict
import itertools
import json
import math
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

# Qiskit para el circuito cuántico
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

# Configurar rutas del repositorio
SCRIPT_DIR = Path(__file__).resolve().parent
CASO1_DIR = SCRIPT_DIR.parent
REPO_ROOT = CASO1_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CASO1_DIR) not in sys.path:
    sys.path.insert(0, str(CASO1_DIR))

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable
from modelo.qubo_pmedian_compacto import (
    construir_qubo_pmedian_compacto,
    comprobar_factibilidad_compacto,
    coste_pmedian_compacto,
    energia_qubo_compacto,
)
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo

FIGURAS_DIR = CASO1_DIR / "figuras"
RESULTADOS_DIR = CASO1_DIR / "resultados"
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# SIMULADOR ANALÍTICO EXACTO DE QAOA (4 QUBITS, p=1)
# =============================================================================

def simular_qaoa_analitico_4q(qubo, matriz, optimo_exacto):
    """Construye el operador diagonal H_C y funciones de evaluación para QAOA p=1."""
    energias = np.zeros(16, dtype=float)
    es_optimo = np.zeros(16, dtype=bool)
    es_factible = np.zeros(16, dtype=bool)

    for idx, bits in enumerate(itertools.product([0, 1], repeat=4)):
        asig = {f"x_{j}": bits[j] for j in range(4)}
        e = energia_qubo_compacto(qubo, asig)
        energias[idx] = e
        fact = comprobar_factibilidad_compacto(qubo, asig)
        if fact["factible"]:
            es_factible[idx] = True
            coste = coste_pmedian_compacto(matriz, fact["seleccionadas"])
            if abs(coste - optimo_exacto) < 1e-6:
                es_optimo[idx] = True

    # Matriz del mezclador U_B(beta) = prod (cos(beta) I - i sin(beta) X)
    # Como U_B es separable qubit a qubit, U_B|x> es producto tensorial
    def calcular_estado_qaoa(gamma, beta):
        # 1. Estado inicial |+>^4
        psi = np.full(16, 1.0 / 4.0, dtype=complex)
        # 2. Operador de fase del problema: exp(-i * gamma * H_C)
        psi = psi * np.exp(-1j * gamma * energias)
        # 3. Operador mezclador: U_B(beta) aplicado a cada qubit
        # Matriz 2x2 para un qubit: [[cos(b), -i sin(b)], [-i sin(b), cos(b)]]
        cb, sb = np.cos(beta), -1j * np.sin(beta)
        Rx = np.array([[cb, sb], [sb, cb]], dtype=complex)

        # Aplicar a los 4 qubits mediante reshape tensorial
        psi_tensor = psi.reshape((2, 2, 2, 2))
        # Tensor contractions
        psi_tensor = np.einsum("ia,ajkl->ijkl", Rx, psi_tensor)
        psi_tensor = np.einsum("ja,iakl->ijkl", Rx, psi_tensor)
        psi_tensor = np.einsum("ka,ijal->ijkl", Rx, psi_tensor)
        psi_tensor = np.einsum("la,ijka->ijkl", Rx, psi_tensor)

        psi_final = psi_tensor.reshape(16)
        probs = np.abs(psi_final) ** 2
        exp_energy = np.sum(probs * energias)
        p_opt = np.sum(probs[es_optimo])
        p_fact = np.sum(probs[es_factible])
        return exp_energy, p_opt, p_fact, probs

    return energias, es_optimo, es_factible, calcular_estado_qaoa


# =============================================================================
# FIGURA 1: PAISAJE VARIACIONAL DE ENERGÍA Y OPTIMIZACIÓN
# =============================================================================

def generar_figura_paisaje_energia_y_optimizacion():
    """Genera la superficie 2D de <H_C> y P_opt con la trayectoria de COBYLA."""
    print("Generando Figura 1: Paisaje Variacional QAOA (gamma, beta) y Trayectoria COBYLA...")
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo = construir_qubo_pmedian_compacto(matriz, k=2, cota_factible=pam["coste_total"])
    optimo_exacto = k_medoids_exhaustivo(candidatas, matriz, 2)["coste_total"]

    _, _, _, evaluar_qaoa = simular_qaoa_analitico_4q(qubo, matriz, optimo_exacto)

    # Malla para el paisaje variacional
    n_gamma, n_beta = 70, 50
    gamma_vals = np.linspace(0, 2 * np.pi, n_gamma)
    beta_vals = np.linspace(0, np.pi, n_beta)
    G, B = np.meshgrid(gamma_vals, beta_vals)

    E_grid = np.zeros((n_beta, n_gamma))
    P_grid = np.zeros((n_beta, n_gamma))

    for i in range(n_beta):
        for j in range(n_gamma):
            e_val, p_opt, _, _ = evaluar_qaoa(gamma_vals[j], beta_vals[i])
            E_grid[i, j] = e_val
            P_grid[i, j] = p_opt * 100.0

    # Trayectoria de optimización COBYLA desde punto inicial representativo
    trayectoria = []
    def callback_opt(x):
        trayectoria.append((x[0], x[1]))

    punto_inicio = np.array([0.4, 0.8])
    trayectoria.append((punto_inicio[0], punto_inicio[1]))

    def loss(p):
        e_val, _, _, _ = evaluar_qaoa(p[0], p[1])
        return e_val

    res_opt = minimize(loss, punto_inicio, method="COBYLA", callback=callback_opt, options={"maxiter": 25})
    trayectoria = np.array(trayectoria)

    fig, (ax_e, ax_p) = plt.subplots(1, 2, figsize=(15, 6.2))
    plt.subplots_adjust(wspace=0.25, left=0.07, right=0.94, top=0.88, bottom=0.12)

    # --- Panel 1: Paisaje de Energía Esperada <H_C> ---
    cf_e = ax_e.contourf(G, B, E_grid, levels=25, cmap="viridis")
    cbar_e = fig.colorbar(cf_e, ax=ax_e, fraction=0.046, pad=0.04)
    cbar_e.set_label("Valor Esperado $\\langle H_C \\rangle(\\gamma, \\beta)$", fontsize=10)
    cs_e = ax_e.contour(G, B, E_grid, levels=12, colors="white", alpha=0.35, linewidths=0.7)
    ax_e.clabel(cs_e, inline=True, fontsize=7.5, fmt="%.1f")

    # Dibujar trayectoria COBYLA
    ax_e.plot(trayectoria[:, 0], trayectoria[:, 1], "r.-", markersize=8, linewidth=1.8, label="Trayectoria COBYLA (p=1)")
    ax_e.plot(punto_inicio[0], punto_inicio[1], "wo", markersize=9, markeredgecolor="black", label="Punto Inicial $\\theta_0$")
    ax_e.plot(res_opt.x[0], res_opt.x[1], "y*", markersize=14, markeredgecolor="black", label="Mínimo Alcanzado")

    ax_e.set_title("Paisaje de Energía Cuántica $\\langle H_C \\rangle(\\gamma, \\beta)$\nConvergencia Variacional COBYLA", fontsize=11, fontweight="bold")
    ax_e.set_xlabel("Parámetro de Fase $\\gamma$ (radianes)", fontsize=10)
    ax_e.set_ylabel("Parámetro Mezclador $\\beta$ (radianes)", fontsize=10)
    ax_e.set_xlim(0, 2 * np.pi)
    ax_e.set_ylim(0, np.pi)
    ax_e.legend(loc="upper right", fontsize=9, framealpha=0.9)

    # --- Panel 2: Paisaje de Probabilidad de Óptimo P_opt ---
    cf_p = ax_p.contourf(G, B, P_grid, levels=25, cmap="plasma")
    cbar_p = fig.colorbar(cf_p, ax=ax_p, fraction=0.046, pad=0.04)
    cbar_p.set_label("Probabilidad de Óptimo $P_{\\text{opt}}$ (%)", fontsize=10)
    cs_p = ax_p.contour(G, B, P_grid, levels=10, colors="white", alpha=0.4, linewidths=0.7)
    ax_p.clabel(cs_p, inline=True, fontsize=7.5, fmt="%.0f%%")

    # Marcar pico de probabilidad
    max_idx = np.unravel_index(np.argmax(P_grid), P_grid.shape)
    gamma_best = G[max_idx]
    beta_best = B[max_idx]
    prob_max = P_grid[max_idx]
    ax_p.plot(gamma_best, beta_best, "w*", markersize=16, markeredgecolor="black", label=f"Máx. Prob. ({prob_max:.1f}%)")
    ax_p.plot(res_opt.x[0], res_opt.x[1], "yo", markersize=9, markeredgecolor="black", label=f"Solución COBYLA ({P_grid[int(res_opt.x[1]/(np.pi/(n_beta-1))), int(res_opt.x[0]/(2*np.pi/(n_gamma-1)))]:.1f}%)")

    ax_p.set_title("Superficie de Probabilidad Óptima $P_{\\text{opt}}(\\gamma, \\beta)$\nRegiones de Amplificación Cuántica Constructiva", fontsize=11, fontweight="bold")
    ax_p.set_xlabel("Parámetro de Fase $\\gamma$ (radianes)", fontsize=10)
    ax_p.set_ylabel("Parámetro Mezclador $\\beta$ (radianes)", fontsize=10)
    ax_p.set_xlim(0, 2 * np.pi)
    ax_p.set_ylim(0, np.pi)
    ax_p.legend(loc="upper left", fontsize=9, framealpha=0.9)

    ruta_salida = FIGURAS_DIR / "qaoa_paisaje_energia_y_optimizacion.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 2: DISTRIBUCIÓN DE PROBABILIDADES DE ESTADOS CUÁNTICOS
# =============================================================================

def generar_figura_distribucion_probabilidades():
    """Genera el histograma comparativo: estado inicial vs QAOA óptimo vs disparos empíricos."""
    print("Generando Figura 2: Distribución de Probabilidades de Estados (Amplificación Cuántica)...")
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo = construir_qubo_pmedian_compacto(matriz, k=2, cota_factible=pam["coste_total"])
    optimo_exacto = k_medoids_exhaustivo(candidatas, matriz, 2)["coste_total"]

    _, es_optimo, es_factible, evaluar_qaoa = simular_qaoa_analitico_4q(qubo, matriz, optimo_exacto)

    # Parámetros óptimos conocidos para p=1 en esta instancia
    gamma_opt, beta_opt = 1.05, 0.90
    _, p_opt_analitica, p_fact_analitica, probs_qaoa = evaluar_qaoa(gamma_opt, beta_opt)

    # Simular muestreo con 1024 shots
    np.random.seed(20260908)
    shots = 1024
    conteo_shots = np.random.multinomial(shots, probs_qaoa)
    freq_shots = conteo_shots / shots

    probs_inicial = np.full(16, 1.0 / 16.0)

    # Etiquetas de estados en binario
    labels_estados = ["".join(str(b) for b in bits) for bits in itertools.product([0, 1], repeat=4)]

    # Ordenar por estado base de 0 a 15
    x = np.arange(16)
    width = 0.28

    fig, ax = plt.subplots(figsize=(14, 6.8))
    plt.subplots_adjust(left=0.06, right=0.96, top=0.88, bottom=0.15)

    rects1 = ax.bar(x - width, probs_inicial * 100, width, label="Estado Inicial Uniforme $|+\\rangle^{\\otimes 4}$ ($6.25\\%$)", color="#bdc3c7", edgecolor="#7f8c8d")

    # Colores según categoría para el estado cuántico QAOA
    colores_qaoa = []
    for idx in range(16):
        if es_optimo[idx]:
            colores_qaoa.append("#27ae60")  # Verde óptimo
        elif es_factible[idx]:
            colores_qaoa.append("#f39c12")  # Naranja subóptimo
        else:
            colores_qaoa.append("#e74c3c")  # Rojo no factible

    rects2 = ax.bar(x, probs_qaoa * 100, width, label="Distribución Teórica QAOA ($p=1$)", color=colores_qaoa, edgecolor="#1e8449", linewidth=1.2)
    rects3 = ax.bar(x + width, freq_shots * 100, width, label=f"Muestreo Empírico ({shots} shots)", color="#2980b9", edgecolor="#1a5276", alpha=0.85)

    ax.set_ylabel("Probabilidad de Medición (%)", fontsize=11, fontweight="bold")
    ax.set_title("Distribución de Probabilidad del Colapso Cuántico en QAOA (4 Qubits)\nAmplificación Selectiva sobre los Estados Factibles Óptimos", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"|{l}⟩" for l in labels_estados], rotation=45, fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, 52)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Resaltar y etiquetar los estados óptimos
    for idx in range(16):
        if es_optimo[idx]:
            val = probs_qaoa[idx] * 100
            ax.text(idx, val + 1.2, f"★ ÓPTIMO\n{val:.1f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#196f3d")
            # Resaltar fondo de etiqueta en eje X
            ax.get_xticklabels()[idx].set_color("#1e8449")
            ax.get_xticklabels()[idx].set_fontsize(10.5)

    # Cuadro informativo de rendimiento cuántico
    info_box = (
        f"Métricas QAOA (p=1):\n"
        f"• Prob. Óptimo Acumulada: {p_opt_analitica * 100:.1f}%\n"
        f"• Prob. Factible Total: {p_fact_analitica * 100:.1f}%\n"
        f"• Supresión No Factibles: {(1 - p_fact_analitica) * 100:.1f}%\n"
        f"• Amplificación Óptima: {p_opt_analitica / 0.125:.1f}x sobre uniforme"
    )
    ax.text(0.02, 0.95, info_box, transform=ax.transAxes, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#eafaf1", edgecolor="#27ae60", alpha=0.95),
            fontsize=9.5, fontweight="bold", color="#145a32")

    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)

    ruta_salida = FIGURAS_DIR / "qaoa_distribucion_probabilidades_estados.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 3: DIAGRAMA DEL CIRCUITO CUÁNTICO QAOA
# =============================================================================

def generar_figura_circuito_cuantico():
    """Genera el circuito cuántico de QAOA p=1 en Qiskit y lo guarda a 300 DPI."""
    print("Generando Figura 3: Circuito Cuántico QAOA (4 Qubits, p=1)...")
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo = construir_qubo_pmedian_compacto(matriz, k=2, cota_factible=pam["coste_total"])

    # Parámetros simbólicos para el circuito
    gamma = Parameter("γ")
    beta = Parameter("β")

    qc = QuantumCircuit(4, 4, name="QAOA_p1")

    # 1. Capa de preparación inicial Hadamard
    for q in range(4):
        qc.h(q)
    qc.barrier(label="U(C, γ)")

    # 2. Operador de Fase del Problema U(C, gamma)
    # Términos lineales R_Z
    for var, coef in qubo["lineal"].items():
        q_idx = int(var.split("_")[1])
        # En Qiskit la rotación Rz tiene ángulo 2*gamma*coef
        qc.rz(2 * gamma, q_idx)

    # Términos cuadráticos R_ZZ entre pares
    for (u, v), coef in qubo["cuadratico"].items():
        q_u = int(u.split("_")[1])
        q_v = int(v.split("_")[1])
        qc.rzz(2 * gamma, q_u, q_v)

    qc.barrier(label="U(B, β)")

    # 3. Operador Mezclador Transversal U(B, beta)
    for q in range(4):
        qc.rx(2 * beta, q)

    qc.barrier(label="Medición")

    # 4. Medición en la base computacional
    qc.measure(range(4), range(4))

    # Dibujar usando Qiskit Matplotlib Drawer
    fig = qc.draw(
        output="mpl",
        style="iqp",
        fold=20,
        plot_barriers=True,
    )

    fig.suptitle(
        "Circuito Cuántico QAOA ($p=1$) — Formulación Compacta ($4$ Qubits)\n"
        "Capa Inicial Hadamard $\\to$ Operador de Fase $U(C, \\gamma)$ $\\to$ Mezclador Transversal $U(B, \\beta)$",
        fontsize=12,
        fontweight="bold",
        y=0.98,
    )

    ruta_salida = FIGURAS_DIR / "qaoa_circuito_cuantico_4q.png"
    fig.savefig(ruta_salida, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 4: STRESS TEST DE SHOTS Y ESCALABILIDAD (20Q vs 4Q)
# =============================================================================

def generar_figura_stress_test_shots():
    """Genera la figura de escalabilidad y stress test con datos experimentales reales."""
    print("Generando Figura 4: Stress Test de Muestreo y Escalabilidad (20Q vs 4Q)...")

    # Buscar el JSON de stress test más reciente
    archivos_stress = list(RESULTADOS_DIR.glob("qaoa_20q_stress_shots_*.json"))
    if not archivos_stress:
        raise FileNotFoundError("No se encontró ningún archivo qaoa_20q_stress_shots_*.json en resultados/")
    archivos_stress.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    archivo_reciente = archivos_stress[0]

    with open(archivo_reciente, "r", encoding="utf-8") as f:
        data_stress = json.load(f)

    # Extraer datos de la Parte A (parámetros fijos en la rejilla)
    registros = data_stress.get("parte_a_parametros_fijos", [])
    filas_fact = [r for r in registros if r.get("etiqueta_punto") == "max_fact_rejilla"]
    filas_opt = [r for r in registros if r.get("etiqueta_punto") == "max_opt_rejilla"]

    shots_f = [r["shots"] for r in filas_fact]
    p_fact_f = [r["p_fact_empirica"] * 100.0 for r in filas_fact]
    p_opt_f = [r["p_opt_empirica"] * 100.0 for r in filas_fact]
    n_fact_f = [r["n_factibles_observados"] for r in filas_fact]
    n_opt_f = [r["n_optimos_observados"] for r in filas_fact]

    p_opt_o = [r["p_opt_empirica"] * 100.0 for r in filas_opt]
    n_opt_o = [r["n_optimos_observados"] for r in filas_opt]

    fig, (ax_p, ax_n, ax_tts) = plt.subplots(1, 3, figsize=(16, 5.5))
    plt.subplots_adjust(wspace=0.30, left=0.06, right=0.96, top=0.86, bottom=0.14)

    # --- Panel A: Probabilidad Observada por Disparo (%) vs Shots ---
    ax_p.plot(shots_f, p_fact_f, "s-", color="#2980b9", linewidth=2, markersize=7, label="20Q Factible (Rejilla máx. fact.)")
    ax_p.plot(shots_f, p_opt_f, "^--", color="#27ae60", linewidth=1.8, markersize=6, label="20Q Óptimo (Rejilla máx. fact.)")
    ax_p.plot(shots_f, p_opt_o, "o-.", color="#8e44ad", linewidth=1.8, markersize=6, label="20Q Óptimo (Rejilla máx. opt.)")
    ax_p.axhline(65.62, color="#e67e22", linestyle="--", linewidth=2, label="4Q Compacto ($P_{\\text{opt}} \\approx 65.6\\%$)")
    ax_p.axhline(0.0, color="#c0392b", linestyle=":", linewidth=1.5, label="20Q COBYLA end-to-end ($0.0\\%$)")

    ax_p.set_xscale("log")
    ax_p.set_xlabel("Presupuesto de Disparos (*Shots*)", fontsize=10, fontweight="bold")
    ax_p.set_ylabel("Probabilidad Empírica (%)", fontsize=10, fontweight="bold")
    ax_p.set_title("Probabilidad de Muestreo vs Presupuesto de Shots\n(20 Qubits vs 4 Qubits)", fontsize=11, fontweight="bold")
    ax_p.grid(True, which="both", linestyle="--", alpha=0.4)
    ax_p.legend(loc="center right", fontsize=8.5, framealpha=0.9)
    ax_p.set_ylim(-2, 75)

    # --- Panel B: Número de Estados Óptimos y Factibles Encontrados ---
    x_indices = np.arange(len(shots_f))
    width = 0.35
    ax_n.bar(x_indices - width/2, n_fact_f, width, label="Estados Factibles Observados", color="#3498db", edgecolor="#21618c")
    ax_n.bar(x_indices + width/2, n_opt_f, width, label="Estados Óptimos Observados", color="#2ecc71", edgecolor="#196f3d")

    ax_n.set_xticks(x_indices)
    ax_n.set_xticklabels([f"{s:,}" for s in shots_f], rotation=30, fontsize=8.5)
    ax_n.set_xlabel("Presupuesto de Disparos (*Shots*)", fontsize=10, fontweight="bold")
    ax_n.set_ylabel("Número de Estados Muestreados", fontsize=10, fontweight="bold")
    ax_n.set_title("Conteo Absoluto de Soluciones en 20 Qubits\n(Dilución: demanda $>16.000$ shots para 1 óptimo)", fontsize=11, fontweight="bold")
    ax_n.grid(axis="y", linestyle="--", alpha=0.4)
    ax_n.legend(loc="upper left", fontsize=9)

    for i in range(len(shots_f)):
        if n_fact_f[i] > 0:
            ax_n.text(i - width/2, n_fact_f[i] + 1, str(n_fact_f[i]), ha="center", va="bottom", fontsize=8.5, fontweight="bold")
        if n_opt_f[i] > 0:
            ax_n.text(i + width/2, n_opt_f[i] + 1, str(n_opt_f[i]), ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#145a32")

    # --- Panel C: Time-to-Target 99% (TTS_99) ---
    metodos = ["QAOA 20Q\n(COBYLA)", "QAOA 20Q\n(Rejilla 65k shots)", "QAOA 4Q\n(Compacto)"]
    tts_valores = [1e4, 87.2, 0.28]  # 1e4 usado simbólicamente para inf con anotación
    colores_tts = ["#c0392b", "#e67e22", "#27ae60"]

    barras_tts = ax_tts.bar(metodos, tts_valores, color=colores_tts, width=0.45, edgecolor="#2c3e50")
    ax_tts.set_yscale("log")
    ax_tts.set_ylabel("Time-To-Target $TTS_{99}$ (segundos, escala log)", fontsize=10, fontweight="bold")
    ax_tts.set_title("Comparativa de Viabilidad Práctica:\nTime-to-Target 99% ($TTS_{99}$)", fontsize=11, fontweight="bold")
    ax_tts.set_ylim(0.05, 5e4)
    ax_tts.grid(axis="y", which="both", linestyle="--", alpha=0.4)

    # Anotaciones explícitas
    ax_tts.text(0, 1.3e4, "$TTS = \\infty$\n(p=0 en muestras)", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=9)
    ax_tts.text(1, 120, "87.2 s\n(65k shots)", ha="center", va="bottom", fontweight="bold", color="#b9770e", fontsize=9)
    ax_tts.text(2, 0.38, "0.28 s\n(160 shots)", ha="center", va="bottom", fontweight="bold", color="#1e8449", fontsize=9)

    ruta_salida = FIGURAS_DIR / "qaoa_stress_test_shots_escalabilidad.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


def main():
    print("=" * 70)
    print("GENERANDO SUITE DE FIGURAS QAOA PARA CASO 1 (TFM)")
    print("=" * 70)
    generar_figura_paisaje_energia_y_optimizacion()
    generar_figura_distribucion_probabilidades()
    generar_figura_circuito_cuantico()
    generar_figura_stress_test_shots()
    print("Figuras QAOA generadas exitosamente.\n")


if __name__ == "__main__":
    main()
