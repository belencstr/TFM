"""Resolución de un QUBO mediante Simulated Annealing.

Utiliza dwave.samplers.SimulatedAnnealingSampler sobre el diccionario QUBO
construido por modelo/qubo_pmedian.py.
"""


def _importar_sampler():
    try:
        from dwave.samplers import SimulatedAnnealingSampler
    except ImportError as exc:
        raise ImportError(
            "No se encuentra 'dwave-samplers'. Instálalo con:\n"
            "    python -m pip install dwave-samplers"
        ) from exc

    return SimulatedAnnealingSampler


def convertir_a_diccionario_qubo(qubo):
    """Convierte nuestro QUBO a la representación {(u, v): coeficiente}."""
    Q = {}

    for variable, coeficiente in qubo["lineal"].items():
        Q[(variable, variable)] = float(coeficiente)

    for (u, v), coeficiente in qubo["cuadratico"].items():
        Q[(u, v)] = Q.get((u, v), 0.0) + float(coeficiente)

    return Q


def resolver_qubo_simulated_annealing(
    qubo,
    num_reads=100,
    num_sweeps=1000,
    seed=12345,
):
    """Ejecuta Simulated Annealing y devuelve todas las muestras obtenidas.

    La energía devuelta por sample_qubo no incluye la constante del QUBO,
    por lo que se añade al registrar cada muestra.
    """
    if num_reads <= 0:
        raise ValueError("num_reads debe ser positivo.")
    if num_sweeps <= 0:
        raise ValueError("num_sweeps debe ser positivo.")

    SimulatedAnnealingSampler = _importar_sampler()
    sampler = SimulatedAnnealingSampler()

    Q = convertir_a_diccionario_qubo(qubo)

    sampleset = sampler.sample_qubo(
        Q,
        num_reads=num_reads,
        num_sweeps=num_sweeps,
        seed=seed,
    )

    muestras = []

    for registro in sampleset.data(
        fields=["sample", "energy", "num_occurrences"],
        sorted_by="energy",
    ):
        muestras.append(
            {
                "asignacion": dict(registro.sample),
                "energia_sin_constante": float(registro.energy),
                "energia": float(registro.energy) + qubo["constante"],
                "num_occurrences": int(registro.num_occurrences),
            }
        )

    return {
        "muestras": muestras,
        "num_reads": num_reads,
        "num_sweeps": num_sweeps,
        "seed": seed,
        "numero_variables": qubo["numero_variables"],
        "numero_terminos_cuadraticos": qubo["numero_terminos_cuadraticos"],
    }
