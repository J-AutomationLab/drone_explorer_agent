import os 
import time 
import json 
import threading

import paho.mqtt.client as mqtt 
import base64

import cv2 
import numpy as np 

##### OS #####

DATABASE_IMAGE_PATH = 'your-path-to/database/images' # TODO: update your path
DATABASE_JSON_PATH = 'your-path-to/database/json' # TODO: update your path 

DATABASE_IMAGE_PATH = '/home/hostuser/workspace/colcon_ws/src/Indoor_drone_explorer/database/images' 
DATABASE_JSON_PATH = '/home/hostuser/workspace/colcon_ws/src/Indoor_drone_explorer/database/json_data_demo'
DATABASE_MEMORY_PATH = '/home/hostuser/workspace/colcon_ws/src/Indoor_drone_explorer/database/json_data_memory'
DATABASE_BLIP2_PATH = '/home/hostuser/workspace/colcon_ws/src/Indoor_drone_explorer/database/json_data_blip2'

print(f"Will save in the data folder: {DATABASE_IMAGE_PATH}")
os.makedirs(DATABASE_IMAGE_PATH, exist_ok=True)
os.makedirs(DATABASE_JSON_PATH, exist_ok=True)
os.makedirs(DATABASE_MEMORY_PATH, exist_ok=True)

def load_data(json_data_dir=DATABASE_JSON_PATH, keys_to_check=[]):

    assert os.path.exists(json_data_dir) and os.path.isdir(json_data_dir)
    
    registered_data = {}
    for json_path in sorted(os.listdir(json_data_dir)):
        json_path = os.path.join(json_data_dir, json_path)
        json_data = {}
        with open(json_path, 'r') as f: json_data = json.load(f)

        assert [key in json_data.keys() for key in ['pose7d', 'local_image_path'] + keys_to_check]

        registered_data[json_path] = json_data.copy()
    return registered_data

blip_data = load_data(DATABASE_BLIP2_PATH, ['blip'])

def pose_is_similar(pose1, pose2, tol=1e-4):
    return sum(np.abs(np.array(pose1) - np.array(pose2))) < tol 

def get_blip_data(pose7d):
    #print(pose7d)
    #for v in blip_data.values():
        #print(v['pose7d'])
        #print( pose_is_similar(pose7d, v['pose7d']))
    target_data  = [v['blip'] for v in blip_data.values() if pose_is_similar(pose7d, v['pose7d'])]
    return target_data.pop()

##### MQTT ##### 

MQTT_BROKER = 'localhost'
#MQTT_BROKER = 'mqtt-broker'
MQTT_PORT = 1883
MQTT_TOPICS = {
    'in': {
        'pose7d': 'hardware_in/robot/pose7d',
    },
    'out': {
        'camera': 'hardware_out/camera',
        'pose7d': 'hardware_out/robot/pose7d',
    },
}

TIME_CONTRAINT = .25 # seconds

def reset_last_msg(): 
    return {'image': None, 'pose7d': None, 'time': time.time()}

def last_msg_is_ok(last_msg): 
    local_memory = load_data()
    
    # check if all the keys has a value
    cond_not_empty = all(v is not None for v in last_msg.values())
    if not cond_not_empty: return False 

    # check if the pose is not already registered
    if len(local_memory) > 0:
        known_poses = [x['pose7d'] for x in local_memory.values()]

        cond_pose_is_unknown = not any(pose_is_similar(last_msg['pose7d'], known) for known in known_poses)
        # cond_pose_is_unknown = last_msg['pose7d'] not in known_poses
        if not cond_pose_is_unknown: return False 

    return True

def get_timestamp(t=None):
    if t is None:
        t = time.time()
    return time.strftime("%y%m%d%H%M%S", time.localtime(t))

##### MAIN ##### 

class HWOperator:
    TIME_CONTRAINT = TIME_CONTRAINT

    def __init__(self):
        self._mqtt_client = mqtt.Client()
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self.last_msg = reset_last_msg()

        self._t = threading.Thread(target=self._listen, daemon=True).start()
    
    @property
    def current_pose(self): return self.last_msg.get('pose7d')
    
    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe('hardware_out/camera')
        client.subscribe('hardware_out/robot/pose7d')

    def _on_message(self, client, userdata, msg):
        now = time.time()
        if now - self.last_msg['time'] > self.TIME_CONTRAINT:
            self.last_msg = reset_last_msg()
        
        self.last_msg['time'] = now 

        if msg.topic == 'hardware_out/camera':
            img_data = base64.b64decode(msg.payload)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self.last_msg['image'] = img
        
        elif msg.topic == 'hardware_out/robot/pose7d':
            pose7d = json.loads(msg.payload)
            self.last_msg['pose7d'] = pose7d

        if last_msg_is_ok(self.last_msg):
            timestamp = get_timestamp(self.last_msg['time'])
            image_path = os.path.join(DATABASE_IMAGE_PATH, f'camera_img_{timestamp}.jpg')
            data_path = os.path.join(DATABASE_JSON_PATH, f'data_img_{timestamp}.json')
            try:
                pose7d = self.last_msg['pose7d']
                blip = get_blip_data(pose7d)
                json_data = {
                    'pose7d': pose7d,
                    'local_image_path': image_path,
                    'blip': blip,
                }
                with open(data_path, 'w') as f:
                    json.dump(json_data, f, indent=4)

                image = self.last_msg['image']
                cv2.imwrite(image_path, image)
            except Exception as e:
                raise e
            finally:
                self.last_msg = reset_last_msg()
    
    def _listen(self, timesleep=.01):
        try:
            self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self._mqtt_client.loop_start()
            while True:
                time.sleep(timesleep)

        except Exception as e:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            raise e

    def send_cmd(self, target_pose_list):
        payload = json.dumps(target_pose_list)
        self._mqtt_client.publish('hardware_in/robot/pose7d', payload)

if __name__ == "__main__":

    def send_manual_cmd(hardware_operator):
        import ast
        cmd = input("-> Input the pose7d where to move the robot: [x1, x2, x3, r1, r2, r3, r4]:\n\t")
        cmd = ast.literal_eval(cmd)
        hardware_operator.send_cmd(cmd)
    
    hardware_operator = HWOperator()
    while True:
        send_manual_cmd(hardware_operator)
        pass