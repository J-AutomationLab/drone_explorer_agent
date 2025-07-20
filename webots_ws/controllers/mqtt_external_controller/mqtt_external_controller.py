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
    
class RobotController:
    vmax_tr = .25
    vmax_rt = .15

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
            current_pose = self.pose3d
            
            # rotate in robot space
            # TODO 
            
            # clamp 
            clamped_target_tr = [max(min(x, self.vmax_tr), -self.vmax_tr) for x in target_pose3d]
            clamped_target_pose = np.array(current_pose) + np.array(clamped_target_tr)
            print(current_pose, clamped_target_tr, clamped_target_pose)
            
            self._tf.setSFVec3f(list(clamped_target_pose))
            
        if target_rot4d is not None:
            current_rot = self.rot4d
            
            # rotate in robot space
            # TODO 
            
            # clamp 
            clamped_target_rt = [max(min(x, self.vmax_rt), -self.vmax_rt) for x in target_rot4d]
            clamped_target_rot = np.array(current_rot) + np.array(clamped_target_rt)
            print(current_rot, clamped_target_rt, clamped_target_rot)
            
            self._rf.setSFVec3f(list(clamped_target_rot))

try:
    # MQTT objects
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect 
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883)
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
    
    print(robot_controller.pose3d, robot_controller.rot4d)
    
    cmd_msg = None
    
    while supervisor.step(timestep) != -1:
    
        # read and publish sensors 
        image_bytes = camera.getImage() # class bytes
        if image_bytes:
            img_np = np.frombuffer(image_bytes, dtype=np.uint8).reshape((height, width,4))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            _, jpeg_bytes = cv2.imencode('.jpg', img_bgr)
            
            encoded = base64.b64encode(jpeg_bytes).decode('ascii')
            pose7d = {
                'pose3d': list(robot_controller.pose3d),
                'rot4d': list(robot_controller.rot4d),
            }
            mqtt_client.publish('hardware_out/camera', encoded)
            mqtt_client.publish('hardware_out/robot/pose7d', json.dumps(pose7d))
        
        if cmd_msg is not None:
            topic = cmd_msg.topic
            payload = cmd_msg.payload.decode()
            payload = json.loads(payload)
            
            print(topic, payload)
            if topic == 'hardware_in/robot/pose7d':
                move_pose3d = payload[:3]
                move_rot4d = payload[3:]
                assert [len(x) for x in [move_pose3d, move_rot4d]] == [3,4]
                robot_controller.move(target_pose3d=move_pose3d, target_rot4d=move_rot4d)
            else:
                raise ValueError(f'Received message from unknwon topic: {topic}')
            cmd_msg = None 
        
        time.sleep(1/30)

except Exception as e:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    raise e