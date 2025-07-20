# GLOBAL DESCRIPTION 
This repository is a drone able to find a specific room or object into a controlled indoor environment. 
The main focus has been done on the decision part, not the control part.

## Components
* Simulator: visualisation entity.
* Operator: hardware communication entity.
* Master: reasoning entity.
* Pathfinder: spatial expert entity.
* Archivist: database expert entity.

---
### Simulator 
The simulation is an indoor appartment (from the *amazon github repository*) loaded in the *Webots* simulator. 

#### Drone [MQTT node]
The drone is a simple robot composed of a cone shaped physical drone and an embedded camera:
* The drone is defined in the *FlyingCamera.proto* file.
* The drone does not implement any physics, then is easily controlled. The drone can be controlled from a simple subscription directly updating its pose. 
* The camera in the direction of the cone's base. The picture is taken by the camera and directly published, with the pose. 

The drone publishes and subscribes to the main system using MQTT. Its behavior is defined in the *mqtt_external_controller.py*.

---
### Operator [ROS2 node, MQTT node]
The hardware IO controller is the connection between the main system and the drone:
* The Hardware IO controller is a ROS2 node.
* It receives the sensor data from the MQTT broker, process it and write it in the database. It also can be triggered to command the drone using the MQTT connection.

#### Processes 
* The images yielded by the camera feed is described using BLIP2. The results are then written in the database as a json file. The image is also written in the database, in a separate folder than the json data. The reference to the image is written in the json data.
* Because of limitated ressources, this process cannot be done in real time and has been computed using google colab before the simulation. 

---
### Master [ROS2 node, Langgraph agent]
TODO

---
### Pathfinder [ROS2 node]
TODO

---
### Archivist [ROS2 node]
TODO

## Implemented behavior
TODO 

# INSTALL

TODO 

# EXECUTION 

TODO
