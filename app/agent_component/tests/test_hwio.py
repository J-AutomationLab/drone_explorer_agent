import pytest
import json
import numpy as np
from unittest.mock import patch, MagicMock
from src.hardware_operator import HWOperator, load_data

MOCK_DATABASE_BLIP2_PATH = "/home/hostuser/workspace/database/backup/json_data_blip2"

##### Fixtures #####

@pytest.fixture
def hw_operator():
    # patch MQTT to avoid actual broker connection
    with patch('src.hardware_operator.mqtt.Client') as MockClient:
        hw = HWOperator()
        yield hw

##### Positive tests #####

def test_load_data_positive():
    data = load_data(json_data_dir=MOCK_DATABASE_BLIP2_PATH, keys_to_check=['blip'])
    key = list(data.keys())[0]
    assert data[key]['pose7d'] == [0,0,0,0,0,0,1]
    assert data[key]['blip'] == ["desc"]
    assert isinstance(data[key]['pose7d'], list)
    assert isinstance(data[key]['blip'], list)

def test_hw_operator_initialization(hw_operator):
    assert hasattr(hw_operator, "last_msg")
    assert hw_operator.last_msg['image'] is None
    assert hw_operator.last_msg['pose7d'] is None

def test_send_cmd_calls_publish(hw_operator):
    hw_operator._mqtt_client = MagicMock()
    hw_operator.send_cmd([1,2,3,4,5,6,7])
    hw_operator._mqtt_client.publish.assert_called_with(
        'hardware_in/robot/pose7d', '[1, 2, 3, 4, 5, 6, 7]'
    )

##### Negative tests #####

def test_last_msg_is_ok_no_pose():
    from src.hardware_operator import last_msg_is_ok
    last_msg = {'pose7d': None, 'image': np.zeros((10,10,3))}
    assert last_msg_is_ok(last_msg) is False

def test_last_msg_is_ok_pose_known():
    from src.hardware_operator import last_msg_is_ok
    # mock a known pose
    known_pose = [0, 0, 0, 0, 0, 0, 1]
    last_msg = {'pose7d': known_pose, 'image': np.zeros((10, 10, 3))}
    assert last_msg_is_ok(last_msg) is False
