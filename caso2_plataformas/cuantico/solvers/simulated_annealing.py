from dwave.samplers import SimulatedAnnealingSampler


def resolver_qubo_sa(
    qubo,
    num_reads=100,
    num_sweeps=1000,
    seed=20260826,
):
    sampler = SimulatedAnnealingSampler()

    sampleset = sampler.sample_qubo(
        qubo,
        num_reads=num_reads,
        num_sweeps=num_sweeps,
        seed=seed,
    )

    return sampleset