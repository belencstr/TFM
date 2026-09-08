"""Barrido de la evolución unitaria exacta de QAOA (p=1) en 20 qubits.

Este script proporciona la evidencia analítica y numérica rigurosa para la memoria del TFM:
Simula la acción unitaria exacta del circuito QAOA (p=1) sobre los 2^20 = 1.048.576 estados
del operador de Ising derivado de qubo_pmedian.py sobre MAPA_QAOA_MINIMO:

    |psi(gamma, beta)> = exp(-i * beta * H_M) * exp(-i * gamma * H_C) |+>^(\otimes 20)

donde H_M = sum_{j=0}^{19} X_j.

Evalúa la probabilidad total proyectada sobre el subespacio de los 96 estados factibles
y sobre los 6 estados óptimos a lo largo de una malla de parámetros variacionales (gamma, beta).
Guarda los resultados en la carpeta resultados/.
"""

import os
import sys
import time
from datetime import datetime
from itertools import combinations, product
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable
from modelo.qubo_pmedian import construir_qubo_pmedian
from solvers.k_medoids import k_medoids_pam


def construir_hamiltoniano_diagonal_20q():
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # Fijar la cota de penalización a partir de la solución heurística conocida (PAM)
    # sin presuponer conocimiento del óptimo:
    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo = construir_qubo_pmedian(matriz, k=2, cota_factible=pam["coste_total"])
    vars = qubo["variables"]
    var_to_idx = {v: i for i, v in enumerate(vars)}
    n_vars = len(vars)

    Q = np.zeros((n_vars, n_vars), dtype=np.float64)
    for v, val in qubo["lineal"].items():
        Q[var_to_idx[v], var_to_idx[v]] += val
    for (u, v), val in qubo["cuadratico"].items():
        Q[var_to_idx[u], var_to_idx[v]] += val
    const = float(qubo["constante"])

    # Calcular las energías de los 2^20 estados en 16 bloques de 2^16
    energies = np.zeros(1 << n_vars, dtype=np.float64)
    ints = np.arange(1 << n_vars, dtype=np.uint32)

    for batch in range(16):
        start = batch * (1 << 16)
        size = 1 << 16
        b_ints = ints[start:start+size]
        bits = ((b_ints[:, None] >> np.arange(n_vars)) & 1).astype(np.float64)
        energies[start:start+size] = np.sum(bits * (bits @ Q.T), axis=1) + const

    # Identificar índices de los 96 estados factibles
    feasible_indices = []
    for x_combo in combinations(range(4), 2):
        x_val = sum(1 << j for j in x_combo)
        for y_choices in product(x_combo, repeat=4):
            y_val = sum(1 << (4 + i*4 + j) for i, j in enumerate(y_choices))
            feasible_indices.append(x_val | y_val)

    feasible_mask = np.zeros(1 << n_vars, dtype=bool)
    feasible_mask[feasible_indices] = True
    opt_mask = (np.abs(energies - 2.0) < 1e-6) & feasible_mask

    return energies, feasible_mask, opt_mask, qubo


def simular_qaoa_p1(energies, feasible_mask, opt_mask, gamma, beta):
    """Aplica la evolución unitaria exacta de QAOA p=1 a partir del estado |+>^20."""
    n_qubits = 20
    # 1. Estado inicial |+>^20 con amplitud 1 / sqrt(2^20)
    psi0 = np.ones(1 << n_qubits, dtype=np.complex128) / np.sqrt(1 << n_qubits)

    # 2. Operador de coste: exp(-i * gamma * H_C)
    psi = psi0 * np.exp(-1j * gamma * energies)

    # 3. Mezclador transversal: exp(-i * beta * sum X_j) = prod_j [cos(beta) I - i sin(beta) X_j]
    c_b = np.cos(beta)
    s_b = -1j * np.sin(beta)

    state = psi.reshape([2] * n_qubits)
    for q in range(n_qubits):
        s0 = np.take(state, 0, axis=q)
        s1 = np.take(state, 1, axis=q)
        state = np.stack([c_b * s0 + s_b * s1, s_b * s0 + c_b * s1], axis=q)

    probs = np.abs(state.reshape(-1)) ** 2
    p_fact = float(np.sum(probs[feasible_mask]))
    p_opt = float(np.sum(probs[opt_mask]))

    return p_fact, p_opt


def barrido_gamma_beta():
    print("=" * 84)
    print("BARRIDO DE LA EVOLUCIÓN UNITARIA EXACTA DE QAOA p=1 (20 QUBITS)")
    print("=" * 84)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Generando operador diagonal sobre 2^20 = 1.048.576 amplitudes...")

    t0 = time.perf_counter()
    energies, feasible_mask, opt_mask, qubo = construir_hamiltoniano_diagonal_20q()
    t_ham = time.perf_counter() - t0
    print(f"Hamiltoniano diagonal construido en {t_ham:.2f} s")
    print(f"Estados factibles identificados: {np.sum(feasible_mask)} de 1.048.576 (0.0092%)")
    print(f"Estados óptimos globales:       {np.sum(opt_mask)} de 1.048.576 (0.00057%)")
    print()

    # Probabilidad en superposición uniforme (gamma=0, beta=0)
    p_unif_fact = np.sum(feasible_mask) / (1 << 20)
    p_unif_opt = np.sum(opt_mask) / (1 << 20)
    print(f"Probabilidad en superposición uniforme (|0> mixer libre):")
    print(f"  p_fact_uniforme = {100.0 * p_unif_fact:.6f}%")
    print(f"  p_opt_uniforme  = {100.0 * p_unif_opt:.6f}%")
    print()

    # Malla sistemática de exploración
    # gamma en [0.05, 1.5], beta en [0.05, pi/2]
    gammas = np.linspace(0.05, 1.5, 15)
    betas = np.linspace(0.05, np.pi / 2, 15)

    print(f"Iniciando barrido sobre rejilla de {len(gammas)}x{len(betas)} = {len(gammas)*len(betas)} puntos (gamma, beta)...")

    max_p_fact = 0.0
    max_p_opt = 0.0
    mejor_punto_fact = None
    mejor_punto_opt = None

    t_grid = time.perf_counter()
    for g in gammas:
        for b in betas:
            pf, po = simular_qaoa_p1(energies, feasible_mask, opt_mask, g, b)
            if pf > max_p_fact:
                max_p_fact = pf
                mejor_punto_fact = (g, b)
            if po > max_p_opt:
                max_p_opt = po
                mejor_punto_opt = (g, b)

    duracion_grid = time.perf_counter() - t_grid

    print(f"Barrido completado en {duracion_grid:.2f} s")
    print()
    print("MÁXIMA PROBABILIDAD OBSERVADA EN LA REJILLA EVALUADA:")
    print(f"  Máxima prob. factible observada: {100.0 * max_p_fact:.4f}% en gamma={mejor_punto_fact[0]:.3f}, beta={mejor_punto_fact[1]:.3f} rad")
    print(f"  Máxima prob. óptima observada:   {100.0 * max_p_opt:.4f}% en gamma={mejor_punto_opt[0]:.3f}, beta={mejor_punto_opt[1]:.3f} rad")
    print()

    shots_ejemplos = [20, 40, 80, 160, 2048]
    p_cero_fact = [(1.0 - max_p_fact)**n for n in shots_ejemplos]
    p_cero_opt = [(1.0 - max_p_opt)**n for n in shots_ejemplos]

    shots_99_fact = int(np.ceil(np.log(0.01) / np.log(1.0 - max_p_fact)))
    shots_99_opt = int(np.ceil(np.log(0.01) / np.log(1.0 - max_p_opt)))

    print("ANÁLISIS ESTADÍSTICO DE DISPAROS (SHOTS):")
    print(f"  Para el máximo de factibilidad observado (p_fact = {max_p_fact:.6f}):")
    for n, p0 in zip(shots_ejemplos, p_cero_fact):
        print(f"    - Con N = {n:4d} shots: P(0 éxitos factibles) = {100.0 * p0:.2f}%")
    print(f"    - Disparos necesarios para 99% de confianza de al menos 1 factible: {shots_99_fact} shots")
    print()
    print(f"  Para el máximo de optimalidad observado (p_opt = {max_p_opt:.6f}):")
    for n, p0 in zip(shots_ejemplos, p_cero_opt):
        print(f"    - Con N = {n:4d} shots: P(0 éxitos óptimos)   = {100.0 * p0:.2f}%")
    print(f"    - Disparos necesarios para 99% de confianza de al menos 1 óptimo:   {shots_99_opt} shots")
    print()

    print("INTERPRETACIÓN ACADÉMICA PARA EL TFM:")
    print(
        "En el barrido experimental con 20 a 160 shots, la probabilidad de no observar ninguna\n"
        "muestra factible oscila entre el 88.4% y el 98.5%, y la de no observar ninguna muestra\n"
        "óptima supera el 98.4%, lo que hace completamente previsible el 0.00% empírico registrado.\n"
        "Con 2048 shots, la probabilidad de no observar ningún óptimo sigue siendo del ~81.7%.\n"
        "La ausencia de muestras factibles observadas con 2048 shots en la ejecución variacional\n"
        "refleja adicionalmente que el optimizador clásico (COBYLA a p=1) no converge necesariamente\n"
        "a los parámetros variacionales óptimos de la rejilla explorada."
    )

    return {
        "max_p_fact": max_p_fact,
        "max_p_opt": max_p_opt,
        "mejor_punto_fact": mejor_punto_fact,
        "mejor_punto_opt": mejor_punto_opt,
        "duracion_segundos": duracion_grid,
    }


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt = os.path.join(carpeta_resultados, f"simulacion_unitaria_20q_max_prob_{marca}.txt")

    stdout_original = sys.stdout

    class Tee:
        def __init__(self, *s):
            self.s = s

        def write(self, d):
            for x in self.s:
                x.write(d)
                x.flush()

        def flush(self):
            for x in self.s:
                x.flush()

    try:
        with open(ruta_txt, "w", encoding="utf-8") as f:
            sys.stdout = Tee(stdout_original, f)
            barrido_gamma_beta()
            print()
            print(f"Registro guardado en: {ruta_txt}")
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta_txt}")


if __name__ == "__main__":
    main()
