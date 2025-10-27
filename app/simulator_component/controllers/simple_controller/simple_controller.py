# controllers/simple_controller/simple_controller.py

from controller import Supervisor
import base64
import time
import socket
import json
import cv2
import numpy as np

import paho.mqtt.client as mqtt

# Global command message shared between MQTT callback and main loop
cmd_msg = None

# ===== MQTT callbacks (define before setup_mqtt so names exist) =====
def on_connect(client, userdata, flags, rc):
    """Subscribe to incoming robot command topic when connected."""
    try:
        client.subscribe("hardware_in/robot/pose7d")
    except Exception as e:
        print(f"[WARN] on_connect subscribe failed: {e}")


def on_message(client, userdata, msg):
    """MQTT callback - store last command message for main loop to consume."""
    global cmd_msg
    # keep it simple: accept only the expected topic
    if msg is None:
        return
    if getattr(msg, "topic", None) == "hardware_in/robot/pose7d":
        cmd_msg = msg

def setup_mqtt(broker="mqtt-broker", port=1883, timeout=60):
    """
    Try to connect to the MQTT broker; return a connected client or None.
    Handles missing or unreachable brokers gracefully.
    """
    try:
        # Quick connectivity check before attempting MQTT connection
        sock = socket.create_connection((broker, port), timeout=2)
        sock.close()
    except Exception as e:
        print(f"[WARN] MQTT broker not reachable ({broker}:{port}): {e}")
        print("[INFO] Running without MQTT (offline mode).")

        return None

    try:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(broker, port, timeout)
        client.loop_start()
        print(f"[INFO] MQTT: connected to {broker}:{port}")
        return client

    except Exception as e:
        print(f"[WARN] MQTT connection failed ({broker}:{port}): {e}")
        return None


# ===== ROBOT CONTROLLER =====
class RobotController:
    def __init__(self, trs_field, rot_field):
        self._tf = trs_field
        self._rf = rot_field

    @property
    def pose3d(self):
        return self._tf.getSFVec3f()

    @property
    def rot4d(self):
        return self._rf.getSFRotation()

    def move(self, target_pose3d=None, target_rot4d=None):
        if target_pose3d is not None:
            assert len(target_pose3d) == 3
            self._tf.setSFVec3f(list(target_pose3d))

        if target_rot4d is not None:
            assert len(target_rot4d) == 4
            self._rf.setSFRotation(list(target_rot4d))


# ===== WEBOTS / main loop helpers =====
def setup_supervisor():
    """Return (supervisor, robot_controller, camera, timestep)."""
    supervisor = Supervisor()
    robot_node = supervisor.getSelf()
    timestep = int(supervisor.getBasicTimeStep())

    robot_controller = RobotController(
        robot_node.getField("translation"),
        robot_node.getField("rotation"),
    )

    camera = supervisor.getDevice("camera")
    camera.enable(timestep)
    return supervisor, robot_controller, camera, timestep


def capture_and_encode(camera, height=480, width=640):
    """
    Capture camera image and return base64-encoded JPEG string, or None.
    Safe if getImage() returns falsy.
    """
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


def handle_command(msg, robot_controller):
    """Decode command message and apply move on robot_controller."""
    if msg is None:
        return
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"[WARN] failed to decode payload: {e}")
        return
    # simple validation
    if not isinstance(payload, (list, tuple)) or len(payload) < 7:
        print(f"[WARN] unexpected payload format: {payload}")
        return
    move_pose3d = payload[:3]
    move_rot4d = payload[3:7]
    robot_controller.move(target_pose3d=move_pose3d, target_rot4d=move_rot4d)


def run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_client=None):
    """Main control loop for robot + optional MQTT integration."""
    global cmd_msg
    cmd_msg = None
    height, width = 480, 640

    try:
        while supervisor.step(timestep) != -1:
            encoded = capture_and_encode(camera, height, width)
            pose7d = list(robot_controller.pose3d) + list(robot_controller.rot4d)

            if encoded and mqtt_client:
                try:
                    mqtt_client.publish("hardware_out/camera", encoded)
                    mqtt_client.publish("hardware_out/robot/pose7d", json.dumps(pose7d))
                except Exception as e:
                    print(f"[WARN] mqtt publish failed: {e}")

            # Return for testing purposes, even if no MQTT
            if encoded:
                return encoded, pose7d

            if cmd_msg is not None:
                handle_command(cmd_msg, robot_controller)
                cmd_msg = None

            time.sleep(1.0 / 30.0)

    except Exception as e:
        raise e


def main():
    mqtt_client = setup_mqtt()
    supervisor, robot_controller, camera, timestep = setup_supervisor()
    try:
        run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_client)
    except Exception as e:
        print(f"[ERROR] Exception in main loop: {e}")
    finally:
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except Exception as e:
                print(f"[WARN] mqtt cleanup failed: {e}")
        print("[INFO] Controller shut down cleanly.")


if __name__ == "__main__":
    main()
