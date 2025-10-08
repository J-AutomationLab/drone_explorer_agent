import pytest
import numpy as np
from unittest.mock import patch
from src.agent import Agent, get_initial_state

##### Fixtures #####

@pytest.fixture
def agent_instance():
    with patch('src.agent.HWOperator') as MockHW:
        mock_hw = MockHW.return_value
        mock_hw.current_pose = [0,0,0,0,0,0,1]
        agent = Agent()
        agent._memory = {}
        yield agent

@pytest.fixture
def initial_state():
    pose = [0,0,0,0,0,0,1]
    return get_initial_state(pose, "Find living room")

##### Positive tests #####

def test_get_initial_state(initial_state):
    assert initial_state['prompt'] == "Find living room"
    assert initial_state['current_pose7d'] == [0,0,0,0,0,0,1]
    assert initial_state['known_poses'] == []
    assert initial_state['current_workflow'] == []

def test_load_memory(agent_instance, initial_state):
    with patch('src.agent_component.src.agent.load_data') as mock_load:
        mock_load.return_value = {"key": {"pose7d": [1]*7, "blip": ["desc"]}}
        state = agent_instance.load_memory(initial_state)
        assert 'load_memory' in state['current_workflow']
        assert state['known_poses'] == [[1]*7]

def test_decision_wait_process(agent_instance, initial_state):
    agent_instance._memory = {"a":1}
    assert agent_instance.decision_wait_process(initial_state) == 'process'
    agent_instance._memory = {}
    assert agent_instance.decision_wait_process(initial_state) == 'wait'

##### Negative tests #####

def test_decision_explore_exploit_edge_cases(agent_instance):
    state = {
        'percentage_of_exploration': 0,
        'prior_scores': np.array([0.1,0.2]),
        'posterior_scores': np.array([0.3,0.4])
    }
    # percentage = 0 -> always explore
    assert agent_instance.decision_explore_exploit(state) == 'explore'

    state['percentage_of_exploration'] = 1
    # percentage = 1 -> always exploit
    assert agent_instance.decision_explore_exploit(state) == 'exploit'
