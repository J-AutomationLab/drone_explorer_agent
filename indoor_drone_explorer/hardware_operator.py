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

print(f"Will save in the data folder: {DATABASE_IMAGE_PATH}")
os.makedirs(DATABASE_IMAGE_PATH, exist_ok=True)
os.makedirs(DATABASE_JSON_PATH, exist_ok=True)

def load_data(json_data_dir=DATABASE_JSON_PATH):

    # check the path to data exists
    assert os.path.exists(json_data_dir) and os.path.isdir(json_data_dir)

    # load data
    registered_data = {}
    for json_path in sorted(os.listdir(json_data_dir)):
        json_path = os.path.join(json_data_dir, json_path)
        json_data = {}
        with open(json_path, 'r') as f:
            json_data = json.load(f)

        # check the keys of the loaded data
        assert [key in json_data.keys() for key in ['pose3d', 'rot4d', 'image_path']]

        registered_data[json_path] = json_data.copy()

    return registered_data

##### MQTT ##### 

MQTT_BROKER = 'localhost'
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

def reset_last_msg(): 
    return {'image': None, 'pose7d': None, 'time': None}

def last_msg_is_ok(last_msg): 

    local_memory = load_data()
    
    # check if all the keys has a value
    cond_not_empty = all(v is not None for v in last_msg.values())
    if not cond_not_empty: return False 

    # check if the pose is not already registered
    print(local_memory)
    if len(local_memory) > 0:
        known_poses = [x['pose7d'] for x in local_memory.values()]
        cond_pose_is_unknown = last_msg['pose7d'] not in known_poses
        print()
        print(last_msg['pose7d'])
        print()
        print(known_poses)
        print()

        if not cond_pose_is_unknown: return False 

    return True

last_msg = reset_last_msg()

def get_timestamp(t=None):
    if t is None:
        t = time.time()
    return time.strftime("%y%m%d%H%M%S", time.localtime(t))

def on_connect(client, userdata, flags, rc):
    client.subscribe('hardware_out/camera')
    client.subscribe('hardware_out/robot/pose7d')

def on_message(client, userdata, msg):
    global last_msg 

    last_msg_time = last_msg['time']
    now = time.time()
    #print(f'Received image on topic {msg.topic} at time {get_timestamp(now)}')
    
    last_msg['time'] = now

    # receive and store locally the image 
    if msg.topic == 'hardware_out/camera':
        img_data  = base64.b64decode(msg.payload)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        last_msg['image'] = img

    # receive and store locally the pose: position 3d + rotation 4d
    elif msg.topic == 'hardware_out/robot/pose7d':
        pose7d = json.loads(msg.payload) # dict with pose3d and rot4d keys
        last_msg['pose7d'] = pose7d
    
    # if all asynchronous data has been received before the timestamp -> synchronize and write the data in the database 
    if last_msg_is_ok(last_msg):
        timestamp = get_timestamp(last_msg['time'])
        image_path = os.path.join(DATABASE_IMAGE_PATH, f'camera_img_{timestamp}.jpg')
        try:
            image = last_msg['image']
            pose7d = last_msg['pose7d']
            cv2.imwrite(image_path, image)
            with open(os.path.join(DATABASE_JSON_PATH, f'data_img_{timestamp}.json'), 'w') as f:
                json_data = {
                    'pose7d': pose7d,
                    'local_image_path': image_path,
                }
                json.dump(json_data, f, indent=4)
        except Exception as e:
            raise e 
        finally:
            last_msg = reset_last_msg()
    
##### MAIN ##### 

class HWOperator:
    def __init__(self, on_connect, on_message):
        self._mqtt_client = mqtt.Client()
        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_message = on_message

        self._t = threading.Thread(target=self._listen, daemon=True).start()
    
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

    def send_cmd(self, payload):
        data = json.dumps(payload)
        self._mqtt_client.publish('hardware_in/robot/pose7d', data)

if __name__ == "__main__":

    def send_manual_cmd(hardware_operator):
        import ast
        cmd = input("-> Input the pose7d where to move the robot: [x1, x2, x3, r1, r2, r3, r4]:\n\t")
        cmd = ast.literal_eval(cmd)
        hardware_operator.send_cmd(cmd)
    
    hardware_operator = HWOperator(on_connect, on_message)
    while True:
        #send_manual_cmd(hardware_operator)
        pass