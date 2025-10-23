# agent_component/tests/test_agent_core.py
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from src.agent import Agent, get_initial_state

MOCK_DATABASE_BLIP2_PATH = "/home/hostuser/workspace/agent_component/tests/json_data_blip2"

@pytest.fixture
def minimal_agent(monkeypatch):
    # Patch HWOperator and SpatialAPI before Agent() is constructed
    FakeHW = MagicMock()
    fake_hw_inst = FakeHW.return_value
    fake_hw_inst.current_pose = [0,0,0,0,0,0,1]
    fake_hw_inst.send_cmd = MagicMock()
    fake_hw_inst._blip_data_path = MOCK_DATABASE_BLIP2_PATH
    monkeypatch.setattr("src.agent.HWOperator", FakeHW)

    FakeSpatial = MagicMock()
    fake_spatial_inst = FakeSpatial.return_value
    # provide deterministic small behaviors
    fake_spatial_inst.get_percentage_of_exploration.return_value = 0.5
    fake_spatial_inst.get_closest_points.return_value = [[[0,0,0,0,0,0,1],[1,1,1,0,0,0,1]]]
    fake_spatial_inst.get_shortest_path.return_value = [[0,0,0,0,0,0,1]]
    monkeypatch.setattr("src.agent.SpatialAPI", FakeSpatial)

    # patch heavy functions so Agent instantiates quickly
    monkeypatch.setattr("src.agent.compute_prior_similarities", lambda *a, **k: None)
    monkeypatch.setattr("src.agent.query_clip", lambda *a, **k: 0.1)
    # create agent
    agent = Agent()
    return agent

def test_load_memory_updates_known_poses(minimal_agent, monkeypatch):
    # patch load_data to return predictable memory
    monkeypatch.setattr("src.agent.load_data", lambda path, keys: {"a": {"pose7d": [1]*7, "blip": ["x"]}})
    state = get_initial_state([0,0,0,0,0,0,1], "Find")
    new_state = minimal_agent.load_memory(state)
    assert 'load_memory' in new_state['current_workflow']
    assert new_state['known_poses'] == [[1]*7]

def test_decision_wait_process_behavior(minimal_agent):
    # when _memory empty -> wait
    minimal_agent._memory = {}
    state = get_initial_state([0,0,0,0,0,0,1], "Find")
    assert minimal_agent.decision_wait_process(state) == 'wait'
    # when memory present -> process
    minimal_agent._memory = {"k":1}
    assert minimal_agent.decision_wait_process(state) == 'process'

def test_decision_explore_exploit_edge_cases(minimal_agent):
    # percentage 0 -> explore
    st = {'percentage_of_exploration': 0, 'prior_scores': np.array([0.1,0.2]), 'posterior_scores': np.array([0.3,0.4])}
    assert minimal_agent.decision_explore_exploit(st) == 'explore'
    st['percentage_of_exploration'] = 1
    assert minimal_agent.decision_explore_exploit(st) == 'exploit'
