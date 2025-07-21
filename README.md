# README 

This repository is a drone able to find a specific room or object into a controlled indoor environment. The main focus of this project is the decision agent and its workflow, not the hardware synchronization nor the control of the physics. Also, since my laptop has a very few computing power, I had to compute some process using google colab. Thus, some results are already precomputed instead of being computed in real time. Also, the spatial data management has been oversimplified with a simple graph.

The system is divided in 3 main components:
* Simulator
* Database 
* Agent 

## Simulator 
The simulation is made using *webots*:
* I designed the robot in the *FlyingCamera.wbo* file. It is a simple cone shape with an embedded camera. 
* The world is basically the *complete appartment* world designed by *amazon* where the robot has been added.
* The robot is controlled by the *mqtt_external_controller.py*. 

### Functionalities
The *mqtt_external_controller.py* regroups the following functions:
* It read the pose7d (pose3d + rotation4d) information and publish it using MQTT. 
* It read the camera feed of the embedded camera and publish the image using MQTT.
* It can read an external command subscribed on MQTT to update its pose7d. 

#### choice of design: Webots
I choose Webots as the simulation engine because I could not make Gazebo work in a docker. When I could, I could not load the world. And I did not want a local install or create a full world by myself. Unlike Gazebo, an efficient docker image with ROS2 and Webots already existed and could be pulled and worked efficiently with this world. 

#### Choice of design: MQTT
I choose MQTT as the communication broker between the Simulator and the Database for the following reasons:
* Even if the docker image I pulled to build my simulator implement ROS2 Foxy, I could not call the ROS2 rclpy library during the call of the controller - probably because of some docker option (with a local install, is should not have been a problem). 
* MQTT is simpler but efficient and popular for the communication between the edge and hardware. I use it to transfer data from the controller to the Agent IO node, also installed inside the docker. However, I could have installed the Agent IO node outside of docker and still access the data (with some annoying changes in the config, obviously)...

#### Choice of design: Processes
Since the hardware is generally limited in processing power, the heavy processes are done in the edge and the controller has been build as light as possible.

## Database 
The database is a big word for a set of folders. Since the data is simple here, this design is good enough:
* The images are stored in the */database/image* folder as jpg files.
* The pose and estimated data are stored in the */database/json* folder as json files.

The database is managed by an *operator.py* node. The database is a parallel component of the agent:
* It manages the communication with the hardware controller using MQTT: it read, process and write the robot's sensor data into the database and publish the command from the agent to the robot. The data arrived asynchronously but this node synchronize the writting of the different MQTT input channels.
* The received pose are not processed and are stored immediatly as it is.
* The received images are stored then their text description is estimated usign BLIP2. BLIP2 has been computed on each possible input image using google colab. In the demonstration system, it directly calls the results from a file.

#### Choice of design: not ROS2
Normally I would recommand using ROS2 for this usecase. But since the system is simplified, the data is written in the database and is not passed directly to the agent as it is in real-time, setting up ROS2 would be a loss of time without any real gain. Indeed, the global architecture will be simplified and the operator will be set as an agent's attribute objet:
* The MQTT input data will still be processed since the *on_message* function is a callback.
* The MQTT command data is triggered by the agent, which does not change anything like this. 

#### Choice of design: using BLIP2
The image description are estimated using BLIP2. The output is a list of text description of the image:
* The first item is the global description of the image, ie without any input prompt. The description is raw and general.
* The following items are the image's descriptions generated from a list of input prompts. The description then can answer a question, or focus on a specific detail. By default, since we alreay know that the robot is supposed to find a specific room, the model answer to the following prompt: *In what place am I?*. Then, we have by default a list of 2 texts descriptions.

This process transforms an image as a text, which will be used by the agent later to easily filter the explored room before exploring. The decision between exploring or exploiting the known image is based on the first description of these images. 

## Agent 