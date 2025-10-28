import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from controllers.simple_controller.robot_controller import RobotController, capture_and_encode
#from src.mqtt_bridge import MQTTBridge

# ===== RobotController tests =====
def test_robotcontroller_move():
    tf, rf = MagicMock(), MagicMock()
    tf.getSFVec3f.return_value = [0, 0, 0]
    rf.getSFRotation.return_value = [0, 0, 0, 0]

    rc = RobotController(tf, rf)
    rc.move([1, 2, 3], [0, 1, 0, 3.14])

    tf.setSFVec3f.assert_called_once_with([1, 2, 3])
    rf.setSFRotation.assert_called_once_with([0, 1, 0, 3.14])

def test_pose_and_rot_properties():
    tf, rf = MagicMock(), MagicMock()
    tf.getSFVec3f.return_value = [5, 6, 7]
    rf.getSFRotation.return_value = [0, 0, 1, 1.57]

    rc = RobotController(tf, rf)
    assert rc.pose3d == [5, 6, 7]
    assert rc.rot4d == [0, 0, 1, 1.57]

# ===== capture_and_encode tests =====
def test_capture_and_encode():
    fake_img = np.random.randint(0, 255, (480, 640, 4), dtype=np.uint8).tobytes()
    camera = MagicMock()
    camera.getImage.return_value = fake_img

    encoded = capture_and_encode(camera)
    assert isinstance(encoded, str)
    assert len(encoded) > 0

def test_capture_and_encode_none():
    camera = MagicMock()
    camera.getImage.return_value = None
    assert capture_and_encode(camera) is None