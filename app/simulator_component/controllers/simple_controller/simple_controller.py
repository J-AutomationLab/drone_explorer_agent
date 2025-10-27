from controller import Supervisor
import paho.mqtt.client as mqtt
import base64
import time 
import json 

import cv2
import numpy as np

def on_connect(client, userdata, flags, rc):
    client.subscribe('hardware_in/robot/pose7d')

def on_message(client, userdata, msg):
    global cmd_msg 
    if msg.topic in ['hardware_in/robot/pose7d',]:
        cmd_msg = msg

# ===== CLASSES ====== 

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

def main():
    """Entry point for running in Webots."""
    try:
        # MQTT objects
        mqtt_broker = 'mqtt-broker'
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect 
        mqtt_client.on_message = on_message
        mqtt_client.connect(mqtt_broker, 1883)
        time.sleep(1)
        mqtt_client.loop_start()

        # WEBOTS 
        supervisor = Supervisor()
        robot_node = supervisor.getSelf()
        timestep = int(supervisor.getBasicTimeStep())
        robot_controller = RobotController(
            robot_node.getField('translation'), 
            robot_node.getField('rotation'),
        )   

        camera = supervisor.getDevice('camera')
        camera.enable(timestep)
        height, width = 480, 640
        cmd_msg = None

        while supervisor.step(timestep) != -1:
            image_bytes = camera.getImage()
            if image_bytes:
                img_np = np.frombuffer(image_bytes, dtype=np.uint8).reshape((height, width, 4))
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                _, jpeg_bytes = cv2.imencode('.jpg', img_bgr)
                encoded = base64.b64encode(jpeg_bytes).decode('ascii')
                pose7d = list(robot_controller.pose3d) + list(robot_controller.rot4d)
                mqtt_client.publish('hardware_out/camera', encoded)
                mqtt_client.publish('hardware_out/robot/pose7d', json.dumps(pose7d))

            if cmd_msg is not None:
                topic = cmd_msg.topic
                payload = json.loads(cmd_msg.payload.decode())
                if topic == 'hardware_in/robot/pose7d':
                    move_pose3d = payload[:3]
                    move_rot4d = payload[3:]
                    robot_controller.move(target_pose3d=move_pose3d, target_rot4d=move_rot4d)
                cmd_msg = None

            time.sleep(1/30)

    except Exception as e:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        raise e

if __name__ == "__main__":
    main()