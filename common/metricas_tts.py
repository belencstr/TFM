"""Definición metodológica unificada de Time-To-Target (TTS) para el TFM.

Para un proceso estocástico (Simulated Annealing, muestreo de estado QAOA o repeticiones de optimización):
- Sea p_success la probabilidad de éxito de una ejecución/lectura elemental.
- Sea confidence el nivel de confianza deseado (por defecto 99%, confidence = 0.99).

El número discreto de repeticiones independientes requeridas para garantizar al menos
un éxito con probabilidad >= confidence es:
    R_99 = ceil( ln(1 - confidence) / ln(1 - p_success) )

El tiempo total estimado (TTS_99) es:
    TTS_99 = R_99 * t_run

Interpretación del parámetro t_run según el algoritmo:
- En Simulated Annealing (SA): t_run corresponde al tiempo medio por lectura individual
  (t_read = tiempo_total / num_reads) ejecutada en CPU clásica.
- En QAOA Variacional Simulado:
  * Nivel de disparo (shot): R_shot_99 caracteriza las mediciones sobre el estado cuántico preparado.
  * Nivel de lote/rutina (batch): R_batch_99 y TTS_batch_99 = R_batch_99 * t_batch caracterizan
    el coste empírico de ejecutar el procedimiento completo en simulación clásica (COBYLA + muestreo),
    no una estimación de tiempo de hardware sobre una QPU real.
"""

import math


def calcular_tts99(p_success, t_run, confidence=0.99):
    """Calcula el número entero discreto de repeticiones R_99 y el tiempo estimado TTS_99.

    Parameters
    ----------
    p_success : float
        Probabilidad empírica de éxito en una ejecución/lectura elemental (en [0, 1]).
    t_run : float
        Tiempo de ejecución de la prueba elemental (en segundos). Debe ser no negativo.
    confidence : float, default=0.99
        Nivel de confianza estadística (típicamente 0.99 para el 99%).

    Returns
    -------
    tuple of (int or float, float)
        (R_99, TTS_99). Si p_success == 0, devuelve (math.inf, math.inf).
    """
    if not (0.0 <= p_success <= 1.0):
        raise ValueError(f"p_success debe pertenecer al intervalo [0, 1]. Recibido: {p_success}")

    if t_run < 0:
        raise ValueError(f"t_run no puede ser negativo. Recibido: {t_run}")

    if p_success <= 0.0:
        return math.inf, math.inf

    if p_success >= 1.0:
        return 1, float(t_run)

    r99 = math.ceil(math.log(1.0 - confidence) / math.log(1.0 - p_success))
    return int(r99), float(r99 * t_run)


if __name__ == "__main__":
    # Autocomprobación matemática
    r, t = calcular_tts99(0.0, 1.0)
    assert math.isinf(r) and math.isinf(t), "Error caso p=0"

    r, t = calcular_tts99(1.0, 0.5)
    assert r == 1 and abs(t - 0.5) < 1e-9, "Error caso p=1"

    # Con p=0.5, ln(0.01)/ln(0.5) = -4.60517 / -0.69315 = 6.6438 -> ceil = 7
    r, t = calcular_tts99(0.5, 0.1)
    assert r == 7 and abs(t - 0.7) < 1e-9, f"Error caso p=0.5: r={r}, t={t}"

    print("[OK] Verificación matemática de common/metricas_tts.py superada con éxito.")
