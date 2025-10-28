# controllers/simple_controller/simple_controller.py
from controller import Supervisor
import time

from src.mqtt_bridge import MQTTBridge  # <--- external bridge
from robot_controller import RobotController, capture_and_encode

# ===== WEBOTS SETUP =====
def setup_supervisor():
    """Initialize Supervisor and robot controller."""
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

def run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_bridge):
    """Main simulation loop with decoupled MQTT bridge."""
    height, width = 480, 640

    while supervisor.step(timestep) != -1:
        encoded = capture_and_encode(camera, height, width)
        pose7d = list(robot_controller.pose3d) + list(robot_controller.rot4d)

        mqtt_bridge.send_image(encoded)
        mqtt_bridge.send_pose(pose7d)

        move_cmd = mqtt_bridge.get_move()
        if move_cmd:
            robot_controller.move(target_pose3d=move_cmd[:3], target_rot4d=move_cmd[3:7])

        time.sleep(1.0 / 30.0)

# ===== ENTRYPOINT ===== 
def main():
    supervisor, robot_controller, camera, timestep = setup_supervisor()
    mqtt_bridge = MQTTBridge()
    try:
        run_main_loop(supervisor, timestep, robot_controller, camera, mqtt_bridge)
    except KeyboardInterrupt:
        print("[INFO] Interrupted.")
    finally:
        mqtt_bridge.close()
        print("[INFO] Controller shut down cleanly.")


if __name__ == "__main__":
    main()
