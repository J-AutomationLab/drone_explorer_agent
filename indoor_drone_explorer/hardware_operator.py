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

print(f"Will save in the data folder: {DATABASE_IMAGE_PATH}")
os.makedirs(DATABASE_IMAGE_PATH, exist_ok=True)
os.makedirs(DATABASE_JSON_PATH, exist_ok=True)

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
    return all(v is not None for v in last_msg.values())

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
    print(f'Received image on topic {msg.topic} at time {get_timestamp(now)}')
    
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
        image = last_msg['image']
        pose7d = last_msg['pose7d']
        pose7d['image_path'] = image_path
        try:
            cv2.imwrite(image_path, image)
            with open(os.path.join(DATABASE_JSON_PATH, f'data_img_{timestamp}.json'), 'w') as f:
                json.dump(pose7d, f, indent=4)
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
        print(payload)

if __name__ == "__main__":
    hardware_operator = HWOperator(on_connect, on_message)
    while True:
        cmd = input("Input the pose7d where to move the robot: [x1, x2, x3, r1, r2, r3, r4]")
        cmd = list(cmd)
        cmd = [float(x) for x in cmd]
        hardware_operator.send_cmd(cmd)