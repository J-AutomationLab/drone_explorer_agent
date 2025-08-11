# README 

## DESCRIPTION

The system is currently divided in two different dockers containers (it was very difficult to merge the requirements for the application in the same docker...):
* The first docker containts the simulator. It runs the webots simulator.
* The second docker contains the system. It runs the agent.
* The communication between the simulator and the system is done using mosquitto.

## SET UP

### SET UP THE COMMUNICATION BROKER

The broker handles the communications between the simulator and the agent. 


Create the docker network:

`docker network create mqtt_net`

Run a docker container in the background:

`docker run -d --name mqtt-broker --network mqtt_net eclipse-mosquitto:2   sh -c "printf 'listener 1883\nallow_anonymous true\n' > /mosquitto/config/mosquitto.conf && \ mosquitto -c /mosquitto/config/mosquitto.conf -v"`

### SET UP THE SIMULATOR IMAGE

Download the docker base:

`docker pull alexnic/ros2_webots_nonvidia:version1`

Run the image with your settings:

`docker run -it -u $(id -u):$(id -g) -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:rw \ -v /path/to/project/root:/home/hostuser/workspace/colcon_ws --device /dev/dri --network mqtt_net --entrypoint /bin/bash your_simulation_image`

In the docker, install the following libraries:

`apt install mosquitto mosquitto-clients`
`pip3 install numpy paho-mqtt opencv-python`
> You may need to exec the container as root to do that... 

Start mosquitto:

`systemctl start mosquitto`
> May be there is some other setup to do, I clearly do not remember all the set up actions for this... 

Try mosquitto:

> Terminal 1: `mosquitto_sub -t "test/topic"`
> Terminal 2: `mosquitto_pub -t "test/topic" -m "Test message"`

---
### RUN THE SIMULATOR 

Run the simulator:

`webots ~/workspace/colcon_ws/src/Indoor_drone_explorer/webots_ws/worlds/my_complete_apartment.wbf`
> You should see a flat seen from above with a conic drone in the entrance hallway. 
> If mosquitto is still open, you should have a message showing the connection between the drone controller and the broker. Otherwise, just restart mosquitto and make sure to be connected.

---
### SET UP THE AGENT IMAGE 

Download the docker base:

`docker pull pytorch/pytorch:2.7.1-cuda11.8-cudnn9-runtime` (or another tag suiting your cuda need).
> You should make sure to have already setup nvidia on your host machine.

Run the image with your settings:

`docker run -it -u $(id -u):$(id -g) -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:rw \ -v /path/to/project/root:/home/hostuser/workspace/colcon_ws --device /dev/dri --gpus all --network mqtt_net --entrypoint /bin/bash your_system_image`

In the docker, install the following libraries:

`apt install mosquitto mosquitto-clients`
`conda install -c conda-forge opencv`
`conda install pillow`
`pip3 install paho-mqtt sentence-transformers transformers`
> You may need to exec the container as root to do that... 
> I had some problem to setup opencv. May be you will have to play with it as well...

Start mosquitto:

`systemctl start mosquitto`
> May be there is some other setup to do, I clearly do not remember all the set up actions for this... 

Try mosquitto:

> Terminal 1: `mosquitto_sub -t "test/topic"`
> Terminal 2: `mosquitto_pub -t "test/topic" -m "Test message"`

---
### RUN THE AGENT

Listen the system decision on a mosquitto publisher:

`mosquitto_sub -h localhost -p 1883 -t hardware_in/robot/pose7d`

Run the agent:

`cd ~/workspace/colcon_ws/src/Indoor_drone_explorer/indoor_drone_explorer`
`python3`
`>>> from agent import *`
`>>> agent = Agent()`
`>>> user_prompt = 'find the kitchen'`
`>>> agent.run(user_prompt)`
> You will have a result like this: 
> 
> {'prompt': 'find the kitchen', 'current_pose7d': [-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606], 'known_poses': [[-0.87, -7.46, 1.25, -0.5776832276006791, -0.5776832276006791, -0.5766837756498129, -2.09], [-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841], [-4.82, -7.44772, 1.24449, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841], [-5.41, -7.4459, 1.24367, -0.5776830771686436, -0.5776830771686436, -0.5766840770351942, -2.089995307179586], [-5.41, -7.4459, 1.24367, 0.1865310645653143, 0.6956492407899829, 0.6937422401298994, 2.76978], [-5.62511, -7.48164, 1.24352, -0.9999970711095111, 0.002260400160736421, 0.0008650800615156003, -1.5676853071795867], [-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606]], 'best_poses': [[-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606], [-5.62511, -7.48164, 1.24352, -0.9999970711095111, 0.002260400160736421, 0.0008650800615156003, -1.5676853071795867], [-5.41, -7.4459, 1.24367, 0.1865310645653143, 0.6956492407899829, 0.6937422401298994, 2.76978], [-5.41, -7.4459, 1.24367, -0.5776830771686436, -0.5776830771686436, -0.5766840770351942, -2.089995307179586], [-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841]], 'prior_scores': array([0.4535868 , 0.35924914, 0.35709518, 0.35021389, 0.33919612]), 'posterior_scores': array([0.47087315, 0.47080266, 0.5011265 , 0.50402105, 0.4151104 ], dtype=float32), 'percentage_of_exploration': 0.6363636363636364, 'current_workflow': ['load_memory', 'process_memory', 'explore'], 'path_to_target_pose7d': [[-5.61966, -5.73164, 1.23808, -0.575815941301038, 0.5794159409340522, 0.5768129411994033, -2.0952053071795866]]}
> 
> You should also have a list of pose published in your mosquitto subscriber.

## RUN THE DEMO

Each time the `agent.run` method, the agent will choose to explore the unexplored environment or exploit the explored environment. For now, this function has to be called manually every time until convergence to the exploitation **COMLPETE BEHAVIOR WILL BE IMPLEMENTED LATER**.

---
### INITIALIZE THE DEMO

* Run the simulator.
* Copy the pose running in the webot's terminal. You may have to pause the simulation to copy easily...
* Run the agent. As explained, paste this pause as the current pose. 

---
### MANAGE THE MEMORY [OPTIONAL]

* Go to `~/workspace/colcon_ws/src/Indoor_drone_explorer/database`.
* To consider the flat as unknown, you can remove all the images located in the `images` folder. If you do, remove the same data located in the `json_data_demo` folder. These folders are linked. If you remove an image, remove also the json data with the same timestamp (and vice versa).
* Normally, the current pose is generated again if the simulator works. 

---
### UPDATE THE AGENT DECISION IN THE SYSTEM

* Copy the last pose of the output of the agent (from the mosquitto terminal or the `path_to_target_pose7d` flag outputed by the agent). 
* Go to the **simulation image's** terminal where the `hardware_controller.py` script is running. Paste it as input as explained in the set up.
* You should see the robot move. If the position is unknown, an image and a json data will be generated in the database. 

---
### COMPUTE THE AGENT AGAIN

Do like the first step until here... after moving to all the positions, the drone will find the best match in the flat. 

## DISCUSSION ABOUT THE DESIGN 
Here is a deeper dive into the design, the functions, the constraints and the tradeoffs. 

## FUNCTIONS AND PROCESSES

This system is an agent controlling a flying drone movements using the camera feed to explore the environment. 
In one process loop: 
* The user gives an order to the drone : "Find yhe kitchen".
* The drone compute a choice between exploring and exploiting the memory. If the memory is empty, the drone will explore. If the environment is fully explored, the drone will exploit.

---
### DRONE OBSERVATION AND CONTROL
The drone's hardware controller listen to the pose estimate and the camera feed. The data is then saved in the database. 
> If the position is already registered, the data is not written. This choice of design is explained more in details later.

The controller can also make the robot moves in the environment.

---
### AGENT DECISION PROCESS

The output of the agent reasoning is the next position. In a first place, the agent compute the choice of exploring or exploiting. 

> If the memory is empty, ie the robot didn't explore at all, the agebt will choose to explore. In the opposite case where the memory is full, ie all the environment has been explored, the agent will choose to exploit the memory. 

> In all the other cases, the agent will compute a probability of exploring or exploiting based on the `percentage_of_exploration` (returned by the `spatial_api`) and the `confidence_score` computed from the data currently registered in the memory (database).
> `PROBABILITY OF EXPLOITING = confidence_score * percentage_of_exploration`. 

> The `confidence_score` is a combination of the `prior_score` (match between the image's BLIP2 description and the user's input prompt) and `posterior_score` (bounded CLIP's output logits using the user's input prompt).

The target pose is then chosen depending of the explore or exploit strategy:
* The position linked to the best confidence match is chosen as the target pose with the exploiting mode.
* The closest position out of the known area is chosen as the target pose with the exploring mode.

---
### KNOWLEDGE UPDATES

During the movement to the target pose, the camera feed and their poses are stored in the database if unknown. Since the agent load the database as its memory at every step, it can use the new information for its next decision.

---
### CONSTRAINTS AND TRADEOFFS

#### TWIN DOCKER IMAGE

The simulator and the agent are the two components of the whole system. Each component has been installed as isolated docker applications. 

This choice had been driven by the difficulty of installing torch in the webots environment and the limited time allowed for the setup.

#### WEBOTS

The first natural choice was to use gazebo in a ros2 docker image. The simulator would have used the `complete_appartment.world` designed by **Amazon** (you can find it freely accessible on their own git repo). 

Unfortunately, setting up a working instance of gazebo was very difficult but possible, but not using the world file. The simplest choice was then to directly pull a ros2 webots docker image (ref the INSTALLATION). 

#### MOSQUITTO COMMUNICATION

Control a robot in webots requires to design a script able to read and set some internal variables. MOSQUITTO has been chosen over ROS2 because using ROS2 in the robot's controller script in the Webots computation space was not possible without a proper investigation. Despite the strenghts of ROS2, investigating it will be time consuming for little value.
> Several language are possible but I chose python by preference and simplicity.

#### ROBOT CONTROL

Since the system focus on the reasoning than the controlling dimension, the robot does not implement any physics for simplicity purposes. The control of the robot movement is then greatly simplified and justify the choice of create the simplest robot possible for this task instead of pulling an existing robot.

#### DISCRETE SPACE 

Because of the lack of a direct and automatic communication between both of the components and because the hardware used to develop this demo was not good enough to run efficiently small LLM or ViT (like BLIP2 or Deepseek-r1), pre-computing some results (BLIP2) using images taken from well chosen locations is a good enough tradeoff for develop this prototype. The `spatial_api.py` script manages the space and implement functions like returning the closest path between two chosen points. 
> The description made by BLIP2 has been made using `google colab`. CLIP and SentenceTransfornmers could be infered efficiently on the dev hardware.

Using a discrete space of 11 different locations, the demo can be shown entirely even running the communication manually and moving to the target position step by step. 

#### LANGGRAPH FRAMEWORK FOR THE AGENT 

`Langgraph` handles perfectly cases where the agent's workflow should be managed with control. Since the workflow is simple, using a `ReAct` agent is therefore useless here. A direct controlled graph can handle the case well enough. 
> In this case, the agent's workflow is:
> * Load the updated memory from the database.
> * Decide between waiting or processing further wrt of if the retrieved knowledge is empty or not. If empty, the process ends here. 
> * Process the memory to retrieve the best priors matches and compute their posterior scores wrt the user prompt. Also get the exploration percentage estimate used in the next step.
> * Decide between explore the environment to gather more memory and increase the chance to find a better match or exploit the memory directly. This choice is randomly made using a decision threshold depending on the prior and posterior match scores and the percentage of exploration. The next target is then chosen in the closest unknown locations (explore) or as the location of the best match of the decision score computed (exploit). If the percentage of exploration is 0. (respectively 1.), the agent always choose to explore (exploit).
> * Compute a path to the target position if note givene and control the movement until there.

### NEXT SYSTEM UPGRADE

WHAT TO INVESTIGATE AND UPGRADE:
* Set up the direct and automatic communication between the simulator and the agent to make the real time possible (and remove the annoying copy-paste of information between these subsystems).
* Upgrade the discrete space as a linear and continue space to make it more realisitic. This system will be a very huge upgrade since the main design is based on this simplification. If the system handles bigger space, the database will need to be far much more robust than a set of jsons.
* If the hardware allows it, computing BLIP2 in real time would be greater and make the system usable on more case scenarios.
* Using real data instead of a simulated environment (or increase the simulation's realism by adding some variance in the space wrt time).
* Monitor and explain the process advance in real time to the user using a LLM. Also, advanced uses of CLIP and BLIP2 would be possible using the power of the LLM.
* Use ROS2 to parallelize the processes of the reasoning agent annd use more advanced feature (like an action to control the movement to the target position instead of a list iteration calls...).

WHAT NOT TO UPGRADE:
* Using a LLM in the agent graph would be costly for no or very low value here.
* Upgrade the robot. Since the point of this system is to develop the reasoning agent instead of the hardware control, this would be of little use for the upgrade of the agent directly. Indeed, the agent finds the next target and call the existing move function. Write a more complex function does not change the agent reasoning.

# AUTHOR
Jerome SUSGIN at bluefox[dot]github[at]gmail[dot]com - Feel free to contact me if you need further information.
