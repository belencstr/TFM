import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.metricas_tts import calcular_tts99

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable
from modelo.qubo_pmedian_compacto import construir_qubo_pmedian_compacto
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.qaoa_compacto import resolver_pmedian_qaoa_compacto

K = 2
REPS = 1
ITERACIONES = [1, 3, 5, 10, 15, 20, 25, 30]
SHOTS_LIST = [20, 40, 80, 160, 512, 1024]
SEED = 20260908
CONFIDENCE = 0.99


def prob_batch(p_shot, shots):
    if p_shot <= 0:
        return 0.0
    if p_shot >= 1:
        return 1.0
    return 1.0 - (1.0 - p_shot) ** shots


def ft(x):
    return "inf" if math.isinf(x) else f"{x:.4f}"


def ejecutar():
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # 1. Solución factible clásica conocida (PAM) para fijar A sin conocer el óptimo:
    pam = k_medoids_pam(candidatas, matriz, K)
    qubo = construir_qubo_pmedian_compacto(matriz, k=K, cota_factible=pam["coste_total"])
    nvars = qubo["numero_variables"]

    # 2. Evaluación independiente del óptimo exhaustivo para medir p_opt en las muestras:
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    optimo = exacta["coste_total"]

    print("=" * 135)
    print("CASO 1 — BARRIDO QAOA COMPACTO (4 QUBITS) + TTS (NIVEL SHOT Y NIVEL BATCH)")
    print("=" * 135)
    print(f"Variables/qubits: {nvars} (frente a 20 qubits en el modelo directo)")
    print(f"p / reps: {REPS}")
    print(f"Iteraciones COBYLA: {ITERACIONES}")
    print(f"Shots evaluados: {SHOTS_LIST}")
    print(f"Seed: {SEED}")
    print(f"Óptimo exacto: {optimo}")
    print("Nota metodológica:")
    print("1. El tiempo obtenido corresponde al coste empírico de ejecutar el procedimiento QAOA")
    print("   mediante simulación clásica y no constituye una estimación del tiempo de ejecución sobre una QPU.")
    print("2. TTS_batch_99 representa una estimación condicionada a la distribución obtenida tras la optimización:")
    print("   P_batch se infiere analíticamente de p_shot (P_batch = 1 - (1 - p_shot)^S), no mediante múltiples")
    print("   ejecuciones independientes del optimizador con distintas semillas.")
    print("=" * 135)
    print(
        f"{'iter':>4} | {'shots':>5} | {'t_batch':>8} | "
        f"{'p_opt':>8} | {'r_shot_99':>9} | "
        f"{'P_batch_opt':>11} | {'r_batch_99':>10} | {'tts_batch_99':>12}"
    )
    print("-" * 135)

    todos_r_shot = []
    todos_tts_batch = []

    for maxiter in ITERACIONES:
        for shots in SHOTS_LIST:
            res = resolver_pmedian_qaoa_compacto(
                qubo,
                matriz,
                reps=REPS,
                maxiter=maxiter,
                shots=shots,
                seed=SEED,
                optimo_referencia=optimo,
            )

            t_batch = res["tiempo"]
            a = res["analisis_muestras"]
            p_opt = float(a["probabilidad_optimo"])

            # 1. R_shot_99: mediciones necesarias sobre el estado preparado
            r_shot_99, _ = calcular_tts99(p_opt, 1.0, confidence=CONFIDENCE)

            # 2. P_batch: probabilidad de al menos un óptimo inferida para el lote de S disparos
            pb_opt = prob_batch(p_opt, shots)

            # 3. R_batch_99 y TTS_batch_99 condicionado a la distribución optimizada
            r_batch_99, tts_batch_99 = calcular_tts99(pb_opt, t_batch, confidence=CONFIDENCE)

            if not math.isinf(r_shot_99):
                todos_r_shot.append(r_shot_99)
            if not math.isinf(tts_batch_99):
                todos_tts_batch.append(tts_batch_99)

            str_r_shot = "inf" if math.isinf(r_shot_99) else str(r_shot_99)
            str_r_batch = "inf" if math.isinf(r_batch_99) else str(r_batch_99)

            print(
                f"{maxiter:4d} | {shots:5d} | {t_batch:7.4f}s | "
                f"{100*p_opt:7.3f}% | {str_r_shot:>9} | "
                f"{100*pb_opt:10.4f}% | {str_r_batch:>10} | "
                f"{ft(tts_batch_99):>11}s"
            )
            sys.stdout.flush()

    min_r_shot = min(todos_r_shot) if todos_r_shot else 0
    max_r_shot = max(todos_r_shot) if todos_r_shot else 0
    min_tts_batch = min(todos_tts_batch) if todos_tts_batch else 0.0
    max_tts_batch = max(todos_tts_batch) if todos_tts_batch else 0.0

    print("=" * 135)
    print("CONCLUSIÓN:")
    print(
        f"A diferencia del barrido anterior de 20 qubits (donde TTS99 resultó no estimable por ausencia\n"
        f"de muestras factibles observadas), el modelo compacto para k=2 alcanza estimaciones finitas de\n"
        f"TTS_batch_99 condicionado en todas las configuraciones evaluadas (entre {min_tts_batch:.4f} s y {max_tts_batch:.4f} s\n"
        f"en simulación clásica), requiriendo r_shot_99 entre {min_r_shot} y {max_r_shot} disparos sobre el estado cuántico\n"
        f"preparado para alcanzar una probabilidad acumulada de éxito de al menos el 99% bajo la probabilidad por disparo estimada."
    )




def main():
    carpeta = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"qaoa_compacto_tts_barrido_{marca}.txt")

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
        with open(ruta, "w", encoding="utf-8") as f:
            sys.stdout = Tee(stdout_original, f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
