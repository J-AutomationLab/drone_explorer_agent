# simulator_component/tests/test_robot_controller.py
import sys
import json
import time
from unittest.mock import MagicMock
import pytest

# Mock Webots controller
sys.modules['controller'] = MagicMock()
from controllers.simple_controller.simple_controller import (
    RobotController,
    run_main_loop,
    capture_and_encode,
    handle_command,
)

# ===== Mock classes =====
class MockField:
    """Mock for Webots Supervisor fields"""
    def __init__(self, value):
        self._value = value

    def getSFVec3f(self):
        return self._value

    def getSFRotation(self):
        return self._value

    def setSFVec3f(self, v):
        self._value = v

    def setSFRotation(self, r):
        self._value = r

class MockCamera:
    """Mock camera with fixed image data"""
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        # generate a fake RGBA image
        self._image = bytes([0, 0, 0, 255] * width * height)

    def getImage(self):
        return self._image

    def enable(self, timestep):
        pass

class MockSupervisor:
    """Mock Webots Supervisor"""
    def __init__(self):
        self._step_count = 0
        self.basicTimeStep = 32
        self.robot_node = MagicMock()
        self.robot_node.getField.side_effect = lambda name: MockField([0.0, 0.0, 0.0] if name=="translation" else [0.0,1.0,0.0,0.0])

    def getSelf(self):
        return self.robot_node

    def getDevice(self, name):
        return MockCamera()

    def getBasicTimeStep(self):
        return self.basicTimeStep

    def step(self, timestep):
        # run only 1 step for testing
        self._step_count += 1
        return -1 if self._step_count > 1 else 0

# ===== Fixtures =====
@pytest.fixture
def mock_fields():
    translation = [0.0, 0.0, 0.0]
    rotation = [0.0, 1.0, 0.0, 0.0]
    return MockField(translation), MockField(rotation)

# ===== RobotController tests =====
def test_pose3d_property(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    assert rc.pose3d == [0.0, 0.0, 0.0]

def test_rot4d_property(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    assert rc.rot4d == [0.0, 1.0, 0.0, 0.0]

def test_move_translation_only(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    rc.move(target_pose3d=[1.0, 2.0, 3.0])
    assert rc.pose3d == [1.0, 2.0, 3.0]
    assert rc.rot4d == [0.0, 1.0, 0.0, 0.0]

def test_move_rotation_only(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    rc.move(target_rot4d=[0.0, 0.0, 1.0, 1.57])
    assert rc.rot4d == [0.0, 0.0, 1.0, 1.57]
    assert rc.pose3d == [0.0, 0.0, 0.0]

def test_move_both_translation_and_rotation(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    rc.move(target_pose3d=[1.0, 1.0, 1.0], target_rot4d=[0.0,0.0,1.0,3.14])
    assert rc.pose3d == [1.0, 1.0, 1.0]
    assert rc.rot4d == [0.0,0.0,1.0,3.14]

# ===== New tests for main loop without MQTT =====
def test_run_main_loop_no_mqtt(monkeypatch):
    """
    Run main loop with a mock supervisor and camera, no mqtt_client.
    Should return encoded image and pose7d on first publish attempt.
    """
    supervisor = MockSupervisor()
    robot_controller = RobotController(
        supervisor.getSelf().getField("translation"),
        supervisor.getSelf().getField("rotation")
    )
    camera = supervisor.getDevice("camera")

    # Patch time.sleep to avoid delay
    monkeypatch.setattr("time.sleep", lambda x: None)

    # run_main_loop should exit after first MQTT failure (mqtt_client=None, skip publishing)
    encoded, pose7d = run_main_loop(supervisor, 32, robot_controller, camera, mqtt_client=None)

    assert isinstance(encoded, str)
    assert len(pose7d) == 7
    # verify pose matches robot_controller
    assert pose7d[:3] == robot_controller.pose3d
    assert pose7d[3:] == robot_controller.rot4d

def test_handle_command_moves_robot():
    class Msg:
        payload = json.dumps([1,2,3,0,0,1,1.57]).encode()
    rc = RobotController(MockField([0,0,0]), MockField([0,1,0,0]))
    handle_command(Msg(), rc)
    assert rc.pose3d == [1,2,3]
    assert rc.rot4d == [0,0,1,1.57]
