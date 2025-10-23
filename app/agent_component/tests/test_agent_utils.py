# agent_component/tests/test_utils.py
import numpy as np
from src.agent import compute_prior_score, compute_posterior_score, compute_confidence

def test_compute_prior_posterior_score():
    prior = [0.1, 0.2, 0.3]
    posterior = [0.4, 0.6]
    assert abs(compute_prior_score(prior) - (sum(prior)/len(prior))) < 1e-8
    assert abs(compute_posterior_score(posterior) - (sum(posterior)/len(posterior))) < 1e-8

def test_compute_confidence_shapes_and_values():
    prior = np.array([0.1, 0.2])
    posterior = np.array([0.4, 0.8])
    conf = compute_confidence(prior, posterior)
    assert conf.shape == prior.shape
    # formula: (prior + 3*posterior)/4
    expected = (prior + 3 * posterior) / 4
    assert np.allclose(conf, expected)
