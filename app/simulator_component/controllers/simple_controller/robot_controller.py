import base64
import cv2
import numpy as np

# ===== ROBOT CONTROLLER =====
class RobotController:
    """Encapsulates access to robot position/orientation fields."""
    def __init__(self, trs_field, rot_field):
        self._tf = trs_field
        self._rf = rot_field

    @property
    def pose3d(self):
        """Return translation vector (x, y, z)."""
        return self._tf.getSFVec3f()

    @property
    def rot4d(self):
        """Return rotation vector (axis + angle)."""
        return self._rf.getSFRotation()

    def move(self, target_pose3d=None, target_rot4d=None):
        """Move robot to new translation/rotation if provided."""
        if target_pose3d is not None:
            assert len(target_pose3d) == 3
            self._tf.setSFVec3f(list(target_pose3d))

        if target_rot4d is not None:
            assert len(target_rot4d) == 4
            self._rf.setSFRotation(list(target_rot4d))

# ===== CAMERA HANDLING =====
def capture_and_encode(camera, height=480, width=640):
    """Capture Webots camera frame and return base64 JPEG."""
    image_bytes = camera.getImage()
    if not image_bytes:
        return None
    try:
        img_np = np.frombuffer(image_bytes, dtype=np.uint8).reshape((height, width, 4))
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        _, jpeg_bytes = cv2.imencode(".jpg", img_bgr)
        return base64.b64encode(jpeg_bytes).decode("ascii")
    except Exception as e:
        print(f"[WARN] capture_and_encode failed: {e}")
        return None