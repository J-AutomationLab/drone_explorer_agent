# README 

## DESCRIPTION

The system is currently divided in two different dockers containers (it was very difficult to merge the requirements for the application in the same docker...):
    * The first docker containts the simulator. It runs the webots simulator.
    * The second docker contains the system. It runs the agent.
    * The communication between the simulator and the system is done using mosquitto.

## SET UP

### SET UP THE SIMULATOR IMAGE

Download the docker base:

`docker pull alexnic/ros2_webots_nonvidia:version1`

Run the image with your settings:

`docker run -it -u $(id -u):$(id -g) -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:rw \ -v /path/to/project/root:/home/hostuser/workspace/colcon_ws --device /dev/dri --entrypoint /bin/bash your_simulation_image`

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

Run the hardware_controller script:

`python3 ~/workspace/colcon_ws/src/Indoor_drone_explorer/indoor_drone_explorer/hardware_operator.py`
> You should also see the connection on the mosquitto broker's terminal.
> You should see a list of 7 float running in the simulator's terminal.
> You should have see this message: 
>   Will save in the data folder: /home/hostuser/workspace/colcon_ws/src/Indoor_drone_explorer/database/images
>   hardware_operator.py:103: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
>     self._mqtt_client = mqtt.Client()
>   -> Input the pose7d where to move the robot: [x1, x2, x3, r1, r2, r3, r4]:

Try to input manually this list in this terminal (be careful of the spaces and brackets): 

`[-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841]`
> You should see the robot teleported to another position, its camera feed and the position printed in the simulator's terminal changed. This is how we move the robot in this demo.

---
### SET UP THE AGENT IMAGE 

Download the docker base:

`docker pull pytorch/pytorch:2.7.1-cuda11.8-cudnn9-runtime` (or another tag suiting your cuda need).
> You should make sure to have already setup nvidia on your host machine.

Run the image with your settings:

`docker run -it -u $(id -u):$(id -g) -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:rw \ -v /path/to/project/root:/home/hostuser/workspace/colcon_ws --device /dev/dri --gpus all --entrypoint /bin/bash your_system_image`

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
`>>> current_pose = <PASTE THE CURRENT POSITION FROM THE WEBOT TERMINAL HERE>`
`>>> agent.run(user_prompt, current_pose)`
> You will have a result like this: 
> 
> {'prompt': 'find the kitchen', 'current_pose7d': [-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606], 'known_poses': [[-0.87, -7.46, 1.25, -0.5776832276006791, -0.5776832276006791, -0.5766837756498129, -2.09], [-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841], [-4.82, -7.44772, 1.24449, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841], [-5.41, -7.4459, 1.24367, -0.5776830771686436, -0.5776830771686436, -0.5766840770351942, -2.089995307179586], [-5.41, -7.4459, 1.24367, 0.1865310645653143, 0.6956492407899829, 0.6937422401298994, 2.76978], [-5.62511, -7.48164, 1.24352, -0.9999970711095111, 0.002260400160736421, 0.0008650800615156003, -1.5676853071795867], [-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606]], 'best_poses': [[-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606], [-5.62511, -7.48164, 1.24352, -0.9999970711095111, 0.002260400160736421, 0.0008650800615156003, -1.5676853071795867], [-5.41, -7.4459, 1.24367, 0.1865310645653143, 0.6956492407899829, 0.6937422401298994, 2.76978], [-5.41, -7.4459, 1.24367, -0.5776830771686436, -0.5776830771686436, -0.5766840770351942, -2.089995307179586], [-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841]], 'prior_scores': array([0.4535868 , 0.35924914, 0.35709518, 0.35021389, 0.33919612]), 'posterior_scores': array([0.47087315, 0.47080266, 0.5011265 , 0.50402105, 0.4151104 ], dtype=float32), 'percentage_of_exploration': 0.6363636363636364, 'current_workflow': ['load_memory', 'process_memory', 'explore'], 'path_to_target_pose7d': [[-5.61966, -5.73164, 1.23808, -0.575815941301038, 0.5794159409340522, 0.5768129411994033, -2.0952053071795866]]}
> 
> You should also have a list of pose published in your mosquitto subscriber.

## RUN THE DEMO

I did not have the time to set up the connection between the docker images, so the information will be passed manually (sorry for that)... But it's not so bad, since you input manually the information, you have time to analyse the system behavior. In all cases, this system is not ready for something else than a demo since I had to make it simpler... 

---
### INITIALIZE THE DEMO

* Run the simulator.
* Copy the pose running in the webot's terminal. You may have to pause the simulation to copy easily...
* Run the agent. As explained, paste this pause as the current pose. 

### MANAGE THE MEMORY [OPTIONAL]

* Go to `~/workspace/colcon_ws/src/Indoor_drone_explorer/database`.
* To consider the flat as unknown, you can remove all the images located in the `images` folder. If you do, remove the same data located in the `json_data_demo` folder. These folders are linked. If you remove an image, remove also the json data with the same timestamp (and vice versa).
* Normally, the current pose is generated again if the simulator works. 

### UPDATE THE AGENT DECISION IN THE SYSTEM

* Copy the last pose of the output of the agent (from the mosquitto terminal or the `path_to_target_pose7d` flag outputed by the agent). 
* Go to the **simulation image's** terminal where the `hardware_controller.py` script is running. Paste it as input as explained in the set up.
* You should see the robot move. If the position is unknown, an image and a json data will be generated in the database. 

### COMPUTE THE AGENT AGAIN

Do like the first step until here... after moving to all the positions, the drone will find the best match in the flat. 

## DISCUSSION ABOUT THE DESIGN 

### TWIN DOCKER IMAGE
... 

### WEBOTS
...

### MOSQUITTO COMMUNICATION
...

### LANGGRAPH FRAMEWORK FOR THE AGENT 
...

### DECISION METRICS AND COMPUTATION
...