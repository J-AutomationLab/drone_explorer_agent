# README 

## DESCRIPTION

This repo is the implementation of an AI agent controlling a drone. Its goal is to find a specific room or object into an indoor environment. 

The system is globally composed in 4 components: 
* The AI agent which use the given information to make the drone move.
* The simulator where the drone lives in an indoor apartment. 
* The HMI which allow the user to set the goal and watch the progress.
* The broker which allow the communication between the other components.

### === Use case === 

The drone is located anywhere into the indoor flat. He may already have some knowledge of the place, or not at all. 
* The agent receives the camera and pose estimate of the drone from the simulator. This data is locally stored into the agent memory and is used online to choose the next move.
* The user will set up the goal as a string (like *find the kitchen*), which will be sent to the agent. The agent will then compute an explore-exploit probability depending on its knowledge and the score of similarity between the goal and the data.

## SET UP

*Docker compose* is used to set up the system. Currently, the system is composed of: 
* The agent: Manage the reasoning, data and memory.  
* The simulator: Show the world and the drone, and gather the data to send to the agent.
* The broker: A simple MQTT broker managing the communication between the simulator and the agent. 

> The HMI component is currently not really set up. The user has to set up the goal directly using a public method. 
> 
> The scene is shown directly through the graphic version of the simulator. 
> 
> The HMI component will be developed in the next release. 

To simply build and test the system: 
> `./scripts/app_build_unit_tests.sh` from the **root folder**.
> `chmod +x ./scripts/app_build_unit_tests.sh' to set up the execution rights if needed. 


## RUN 
Enter the following command after having build the docker containers (*docker compose build* or *./scripts/app_build_unit_tests.sh*).

> `docker compose -f ./app/docker_compose.yml up` to start the system.

### === Stop the system === 

> `docker compose -f ./app/docker_compose.yml down` to stop the system.