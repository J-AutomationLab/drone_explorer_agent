import pytest
import json
import numpy as np
from unittest.mock import patch, MagicMock
from src.hardware_operator import HWOperator, load_data, DATABASE_JSON_PATH

##### Fixtures #####

@pytest.fixture
def hw_operator():
    # patch MQTT to avoid actual broker connection
    with patch('src.hardware_operator.mqtt.Client') as MockClient:
        hw = HWOperator()
        yield hw

@pytest.fixture
def sample_json(tmp_path):
    db_path = tmp_path / "json_data"
    db_path.mkdir()
    data = {"pose7d": [0,0,0,0,0,0,1], "local_image_path": "img.jpg", "blip": ["desc"]}
    json_file = db_path / "data.json"
    with open(json_file, "w") as f:
        json.dump(data, f)
    yield db_path

##### Positive tests #####

def test_load_data_positive(sample_json):
    data = load_data(sample_json, ['blip'])
    key = list(data.keys())[0]
    assert data[key]['pose7d'] == [0,0,0,0,0,0,1]
    assert data[key]['blip'] == ["desc"]

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

def test_last_msg_is_ok_no_pose(sample_json):
    from src.hardware_operator import last_msg_is_ok
    last_msg = {'pose7d': None, 'image': np.zeros((10,10,3))}
    assert last_msg_is_ok(last_msg) is False

def test_last_msg_is_ok_pose_known(sample_json):
    from src.hardware_operator import last_msg_is_ok, pose_is_similar
    data = load_data(sample_json, ['blip'])
    pose = list(data.values())[0]['pose7d']
    last_msg = {'pose7d': pose, 'image': np.zeros((10,10,3))}
    assert last_msg_is_ok(last_msg) is False
