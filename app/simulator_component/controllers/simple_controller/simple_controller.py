from controller import Supervisor
import base64
import time 
import json 

import cv2
import numpy as np

# Attempt to import MQTT safely
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

# ===== MQTT Setup & Handlers =====
def setup_mqtt():
    """Try to connect to the MQTT broker; return a connected client or None."""
    if not MQTT_AVAILABLE:
        print("[WARN] paho-mqtt not available, skipping MQTT setup.")
        return None

    try:
        mqtt_broker = "mqtt-broker"
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(mqtt_broker, 1883, 60)
        client.loop_start()
        print(f"[INFO] Connected to MQTT broker at {mqtt_broker}")
        return client
    except Exception as e:
        print(f"[WARN] Could not connect to MQTT broker: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    client.subscribe('hardware_in/robot/pose7d')

def on_message(client, userdata, msg):
    global cmd_msg 
    if msg.topic in ['hardware_in/robot/pose7d',]:
        cmd_msg = msg

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

# ===== WEBOTS CONTROLLER LOGIC =====
def setup_supervisor():
    """Initialize the Webots supervisor, camera, and controller."""
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
    """Capture camera image and return base64-encoded JPEG."""
    image_bytes = camera.getImage()
    if not image_bytes:
        return None

    img_np = np.frombuffer(image_bytes, dtype=np.uint8).reshape((height, width, 4))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
    _, jpeg_bytes = cv2.imencode(".jpg", img_bgr)
    return base64.b64encode(jpeg_bytes).decode("ascii")


def handle_command(cmd_msg, robot_controller):
    """Decode and apply a motion command message."""
    topic = cmd_msg.topic
    payload = json.loads(cmd_msg.payload.decode())

    if topic == "hardware_in/robot/pose7d":
        move_pose3d = payload[:3]
        move_rot4d = payload[3:]
        robot_controller.move(target_pose3d=move_pose3d, target_rot4d=move_rot4d)


def run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_client):
    """Main control loop for robot + MQTT integration."""
    global cmd_msg
    cmd_msg = None
    height, width = 480, 640

    while supervisor.step(timestep) != -1:
        encoded = capture_and_encode(camera, height, width)
        if encoded:
            pose7d = list(robot_controller.pose3d) + list(robot_controller.rot4d)
            if mqtt_client:
                mqtt_client.publish("hardware_out/camera", encoded)
                mqtt_client.publish("hardware_out/robot/pose7d", json.dumps(pose7d))

        if cmd_msg is not None:
            handle_command(cmd_msg, robot_controller)
            cmd_msg = None

        time.sleep(1 / 30)


# ===== MAIN ENTRY POINT =====
def main():
    mqtt_client = setup_mqtt()
    supervisor, robot_controller, camera, timestep = setup_supervisor()

    try:
        run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_client)
    except Exception as e:
        print(f"[ERROR] Exception in main loop: {e}")
    finally:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        print("[INFO] Controller shut down cleanly.")


if __name__ == "__main__":
    main()