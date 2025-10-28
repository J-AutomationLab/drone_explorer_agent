# src/mqtt_bridge.py
import json
import os 
import socket
import paho.mqtt.client as mqtt

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "broker")
MQTT_BROKER_PORT = 1883

class MQTTBridge:
    """Encapsulates MQTT communications for Webots simulation."""

    def __init__(self, broker=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT, timeout=30):
        self.last_cmd = None
        self.client = None
        self.online = False

        # Try broker reachability first
        try:
            sock = socket.create_connection((broker, port), timeout=2)
            sock.close()
        except Exception as e:
            print(f"[WARN] MQTT broker unreachable ({broker}:{port}): {e}")
            print("[INFO] MQTTBridge running in offline mode.")
            raise SystemExit(1)

        try:
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect(broker, port, timeout)
            self.client.loop_start()
            self.online = True
            print(f"[INFO] MQTTBridge connected to {broker}:{port}")
        except Exception as e:
            print(f"[WARN] MQTT connection failed: {e}")

    # ===== Internal callbacks =====
    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe("hardware_in/robot/pose7d")

    def _on_message(self, client, userdata, msg):
        if msg.topic == "hardware_in/robot/pose7d":
            try:
                payload = json.loads(msg.payload.decode())
                if isinstance(payload, (list, tuple)) and len(payload) >= 7:
                    self.last_cmd = payload
            except Exception as e:
                print(f"[WARN] Invalid command payload: {e}")

    # ===== Outgoing data =====
    def send_image(self, encoded_str):
        if not encoded_str:
            return
        if self.online:
            try:
                self.client.publish("hardware_out/camera", encoded_str)
            except Exception as e:
                print(f"[WARN] send_image failed: {e}")
        else:
            print("[OFFLINE] image published.")

    def send_pose(self, pose7d):
        if self.online:
            try:
                self.client.publish("hardware_out/robot/pose7d", json.dumps(pose7d))
            except Exception as e:
                print(f"[WARN] send_pose failed: {e}")
        else:
            print(f"[OFFLINE] pose7d: {pose7d}")

    # ===== Incoming data =====
    def get_move(self):
        """Return latest move command and clear buffer."""
        if self.last_cmd:
            cmd = self.last_cmd
            self.last_cmd = None
            return cmd
        return None

    def close(self):
        """Clean shutdown."""
        if self.online and self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                print(f"[WARN] MQTTBridge close failed: {e}")
