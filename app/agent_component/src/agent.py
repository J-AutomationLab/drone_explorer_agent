import random 
import time 
from typing import TypedDict, Dict, List, Tuple, Any

import cv2 # used only to avoid dynamic import errors
import numpy as np
import torch 
from langgraph.graph import StateGraph, END
from PIL import Image
from sentence_transformers import SentenceTransformer, util
from transformers import CLIPProcessor, CLIPModel

from hardware_operator import HWOperator, load_data, DATABASE_JSON_PATH
from spatial_expert import SpatialAPI

##### models #####

txt_similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
clip_model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
clip_processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', use_fast=False)

##### utils function #####

def compute_similarity_between_2_texts(txt1:str, txt2:str)->float:
    embeddings = txt_similarity_model.encode([txt1,txt2], convert_to_tensor=True)
    return float(util.cos_sim(*embeddings))

def compute_prior_similarities(data:Dict[str, Dict[str, Any]], str_query:str): 
    for k, v_dict in data.items():
        blip_description = v_dict['blip']
        prior_scores = [] 

        # compute similarity for description
        for description in blip_description:
            prior_scores.append(compute_similarity_between_2_texts(description, str_query))
        
        data[k]['prior_scores'] = prior_scores # shape: len(blip_description) 

def query_clip(image_path:str, prompts_per_image:List[str])->float:
    image = Image.open(image_path).convert("RGB")
    inputs = clip_processor(text=prompts_per_image, images=image, return_tensors='pt', padding=True)
    with torch.no_grad():
        outputs = clip_model(**inputs)
        logits_per_image = outputs.logits_per_image.squeeze(0).cpu().numpy()
    
    normalized_output = np.clip((logits_per_image - 0) / (50 - 0), 0, 1) # poor match < 10, good match ~ 15-20, very good > 25-30
    return normalized_output

def compute_prior_score(prior_score_list)->float:
    return np.mean(prior_score_list)

def compute_posterior_score(posterior_score_list)->float:
    return np.mean(posterior_score_list)

def compute_confidence(prior:np.ndarray, posterior:np.ndarray)->np.ndarray:
    return (prior + 3 * posterior) / 4

##### memory state #####
class AgentState(TypedDict):
    prompt: str
    current_pose7d: List[float]
    known_poses: List[List[float]]
    best_poses: List[List[float]]
    prior_scores: List[Tuple[str,float]] 
    posterior_scores: List[Tuple[str,float]] 
    percentage_of_exploration: float 
    current_workflow: List[str] 
    path_to_target_pose7d: List[float]

def get_initial_state(current_pose:List[float], prompt:str)->dict:
    return {
        "prompt": prompt,
        "current_pose7d": current_pose,
        "known_poses": [],
        "best_poses": [],
        "prior_scores": [],
        "posterior_scores": [],
        "percentage_of_exploration": 0.0,
        "current_workflow": [],
        "path_to_target_pose7d": [],
    }

##### agent ##### 
class Agent:

    N_BEST_SIMILARITY_MATCHES = 5

    def __init__(self):
        self._hardware_operator = HWOperator()
        self._spatial_api = SpatialAPI()
        self._agent = self._build()
        self._memory = None 

    def _build(self):
        builder = StateGraph(AgentState)
        builder.add_node('load_memory', self.load_memory)
        builder.add_node('process_memory', self.process_memory) 
        builder.add_node('explore_unknown', self.explore)
        builder.add_node('exploit_known', self.exploit)
        builder.add_node('move_to_target', self.move)

        builder.set_entry_point('load_memory')
        builder.add_conditional_edges(
            'load_memory', self.decision_wait_process, {'process': 'process_memory', 'wait': END}
        )
        builder.add_conditional_edges(
            'process_memory', self.decision_explore_exploit, {'explore': 'explore_unknown', 'exploit': 'exploit_known'}
        )
        builder.add_edge('explore_unknown', 'move_to_target')
        builder.add_edge('exploit_known', 'move_to_target')
        builder.add_edge('move_to_target', END)

        return builder.compile()
    
    def run(self, user_prompt:str, current_pose:List[float]=None)->AgentState:
        current_pose = self._hardware_operator.current_pose if current_pose is None else current_pose 
        initial_state = get_initial_state(current_pose, user_prompt)
        results_state = self._agent.invoke(initial_state)
        return results_state

    # load the database and filter the best matches [mandatory]
    def load_memory(self, state:AgentState)->AgentState:
        self._memory = load_data(DATABASE_JSON_PATH, ['blip'])
        state['known_poses'] = [v['pose7d'] for v in self._memory.values()]
        state['current_workflow'].append('load_memory')

        return state
 
    # if no memory: stop the workflow and wait for the next iteration
    def decision_wait_process(self, state:AgentState)->str:
        return 'process' if len(self._memory) > 0 else 'wait'
    
    # estimate the similarity between the memory and the prompt
    def process_memory(self, state:AgentState)->AgentState:

        N_BEST = 5
        
        prompt = state['prompt']
        known_poses = state['known_poses']
        memory = self._memory
        
        # prior: compare the user prompt with the blip description of the memory and filter the n best 
        compute_prior_similarities(memory, prompt) # update in memory -> priori_scores key in memory.values()
        best_priors_scores = sorted(memory.items(), key=lambda x: compute_prior_score(x[1]['prior_scores']), reverse=True)[:N_BEST] 
        state['best_poses'] = [v[1]['pose7d'] for v in best_priors_scores]
        state['prior_scores'] = np.array([compute_prior_score(x[1]['prior_scores']) for x in best_priors_scores])

        # posterior: estimate the similarity between the user prompt and the best prior images
        clip_matches = [(k, query_clip(data['local_image_path'], prompt)) for k, data in best_priors_scores]
        for k, score in clip_matches:
            self._memory[k]['posterior_scores'] = score 
        state['posterior_scores'] = np.array([compute_posterior_score(x[1]) for x in clip_matches])

        # store the current knowledge wrt the full knowledge
        percentage_of_exploration = self._spatial_api.get_percentage_of_exploration(known_poses)
        state['percentage_of_exploration'] = percentage_of_exploration

        state['current_workflow'].append('process_memory')
        return state
    
    # explore the environment: try to find a better match [optional]
    def explore(self, state:AgentState)->AgentState:
        known_poses = state['known_poses']

        # find the target location using the closest unknown nodes
        closest_points = self._spatial_api.get_closest_points(state['current_pose7d'], known_poses)
        assert len(closest_points) > 0

        # move 
        path_to_target_pose = random.choice(closest_points) # get random trajectory
        assert path_to_target_pose[-1] not in state['known_poses'] # last pose should not be known
        assert all([p in state['known_poses'] for p in path_to_target_pose[:-1]]) # all previous pose should be known
        
        state['path_to_target_pose7d'] = path_to_target_pose

        state['current_workflow'].append('explore')

        return state

    # exploit the memory: go the best registered match [optional]
    def exploit(self, state:AgentState)->AgentState:
        prior_estimation = state['prior_scores']
        posterior_estimation = state['posterior_scores']

        # find the best location in memory
        confidence_array = compute_confidence(prior_estimation, posterior_estimation)
        best_confidence_index = np.argmax(confidence_array)
        best_pose = state['best_poses'][best_confidence_index]
        assert best_pose in state['known_poses']

        # move
        path_to_target_pose = self._spatial_api.get_shortest_path(state['current_pose7d'], best_pose, inputs_as_points=True)
        assert all([p in state['known_poses'] for p in path_to_target_pose])
        state['path_to_target_pose7d'] = path_to_target_pose

        state['current_workflow'].append('exploit')

        return state

    def move(self, state:AgentState) -> AgentState:
        path_to_target = state['path_to_target_pose7d']
        for point in path_to_target:
            self._hardware_operator.send_cmd(point)
            time.sleep(1) # simulate the time to arrive to step pose
        return state 

    # compute the decision between explore and exploit for this step [mandatory]
    def decision_explore_exploit(self, state:AgentState)->str:
        
        percentage_of_exploration = state['percentage_of_exploration']

        # 0 or 100% of exploration cases
        if percentage_of_exploration <= 0: return 'explore'
        if percentage_of_exploration >= 1: return 'exploit'

        # complex decision cases
        prior_estimation = state['prior_scores']
        posterior_estimation = state['posterior_scores']

        # confidence in best matches: prior and posterior estimations
        confidence_array = compute_confidence(prior_estimation, posterior_estimation)
        confidence = np.max(confidence_array)

        # decision based on exploration, confidence and behavior
        exploit_score = percentage_of_exploration * confidence

        # random approach 
        if random.random() <= exploit_score: 
            return "exploit"
        return "explore"

if __name__ == "__main__":
    
    agent = Agent()
    #current_pose = input("Input your current pose as a list of 7 float:\n\t")
    user_prompt = input("Input your command: what room should I find?\n\t ")

    while agent.run(user_prompt)['current_workflow'][-1] != 'exploit':
        results_state = agent.run(user_prompt)
        print(results_state['current_pose7d'], results_state['current_workflow'], results_state['path_to_target_pose7d'])
        print()
    
    print("Found it!")