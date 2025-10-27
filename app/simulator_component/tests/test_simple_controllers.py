# simulator_component/tests/test_robot_controller.py
import sys
from unittest.mock import MagicMock
import pytest

# Mock Webots controller
sys.modules['controller'] = MagicMock()
sys.modules['controller'].Supervisor = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
sys.modules['paho'] = MagicMock()

from controllers.simple_controller.simple_controller import RobotController

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

@pytest.fixture
def mock_fields():
    # Initial translation and rotation
    translation = [0.0, 0.0, 0.0]
    rotation = [0.0, 1.0, 0.0, 0.0]
    return MockField(translation), MockField(rotation)

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
    new_translation = [1.0, 2.0, 3.0]
    rc.move(target_pose3d=new_translation)
    assert rc.pose3d == new_translation
    # rotation should remain unchanged
    assert rc.rot4d == [0.0, 1.0, 0.0, 0.0]

def test_move_rotation_only(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    new_rotation = [0.0, 0.0, 1.0, 1.57]
    rc.move(target_rot4d=new_rotation)
    assert rc.rot4d == new_rotation
    # translation should remain unchanged
    assert rc.pose3d == [0.0, 0.0, 0.0]

def test_move_both_translation_and_rotation(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    new_translation = [1.0, 1.0, 1.0]
    new_rotation = [0.0, 0.0, 1.0, 3.14]
    rc.move(target_pose3d=new_translation, target_rot4d=new_rotation)
    assert rc.pose3d == new_translation
    assert rc.rot4d == new_rotation

def test_move_invalid_translation_length(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    with pytest.raises(AssertionError):
        rc.move(target_pose3d=[1.0, 2.0])  # only 2 elements

def test_move_invalid_rotation_length(mock_fields):
    tf, rf = mock_fields
    rc = RobotController(tf, rf)
    with pytest.raises(AssertionError):
        rc.move(target_rot4d=[0.0, 1.0, 0.0])  # only 3 elements
