import random 
import time 
from typing import TypedDict, Dict, List, Tuple, Any

import numpy as np
import torch 
from langgraph.graph import StateGraph, END
from PIL import Image
from sentence_transformers import SentenceTransformer, util
from transformers import CLIPProcessor, CLIPModel

from hardware_operator import HWOperator, load_data, DATABASE_MEMORY_PATH
from spatial_expert import SpatialAPI

##### models #####

txt_similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
clip_model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
clip_processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', use_fast=False)

##### utils function #####

def compute_similarity_between_2_texts(txt1:str, txt2:str)->float:
    embeddings = [txt_similarity_model.encode(txt, convert_to_tensor=True) for txt in [txt1,txt2]]
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

def compute_confidence(prior, posterior):
    return (prior + 3 * posterior) / 4

##### memory state #####
class AgentState(TypedDict):
    prompt: str
    current_pose7d: List[float]
    known_poses: List[List[float]]
    prior_scores: List[Tuple[str,float]] 
    posterior_scores: List[Tuple[str,float]] 
    percentage_of_exploration: float 
    current_workflow: List[str] 
    target_pose7d: List[float]

def get_initial_state(current_pose:List[float], prompt:str)->dict:
    return {
        "prompt": prompt,
        "current_pose7d": current_pose,
        "known_poses": [],
        "prior_scores": [],
        "posterior_scores": [],
        "percentage_of_exploration": 0.0,
        "current_workflow": [],
        "target_pose7d": [],
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
    
    def run(self, user_prompt):
        current_pose = self._hardware_operator.current_pose
        initial_state = get_initial_state(current_pose, user_prompt)
        results = self._agent.invoke(initial_state)['decision']
        return results

    # load the database and filter the best matches [mandatory]
    def load_memory(self, state:AgentState)->AgentState:
        self._memory = load_data(DATABASE_MEMORY_PATH, ['blip'])
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
        state['prior_scores'] = [compute_prior_score(x[1]['prior_scores']) for x in best_priors_scores]

        # posterior: estimate the similarity between the user prompt and the best prior images
        clip_matches = [(k, query_clip(data['local_image_path'], prompt)) for k, data in best_priors_scores]
        for k, score in clip_matches:
            self._memory[k]['posterior_score'] = score 
        state['posterior_score'] = [compute_posterior_score(x[1]) for x in clip_matches]

        # store the current knowledge wrt the full knowledge
        percentage_of_exploration = self._spatial_api.get_percentage_of_exploration(known_poses)
        state['percentage_of_exploration'] = percentage_of_exploration

        state['current_workflow'].append('process_memory')
        return state
    
    # explore the environment: try to find a better match [optional]
    def explore(self, state:AgentState)->AgentState:
        state['decision'] = 'explore'
        known_poses = [d['pose7d'] for d in load_data(DATABASE_MEMORY_PATH).values()]

        # find the target location using the closest unknown nodes
        closest_points = self._spatial_api.get_closest_points(state['current_pose7d'], known_poses)
        assert len(closest_points) > 0

        # move 
        target_pose = random.choice(closest_points)
        state['target_pose7d'] = target_pose

        return state

    # exploit the memory: go the best registered match [optional]
    def exploit(self, state:AgentState)->AgentState:
        state['decision'] = 'exploit'
        best_posterior = state['posterior_score']

        # find the target location using the best score 
        scores = [x['posterior_score'] for x in self._memory.values()]
        assert best_posterior in scores 

        target_index = scores.index(best_posterior)

        # move 
        target_pose = list(self._memory.values())[target_index]['pose7d']
        state['target_pose7d'] = target_pose

        return state

    def move(self, state:AgentState) -> AgentState:
        path_to_target = self._spatial_api.get_shortest_path(state['current_pose7d'], state['target_pose7d'])
        for path in path_to_target:
            self._hardware_operator.send_cmd(path)
            time.sleep(1) # simulate the time to arrive to step pose
        return state 

    # compute the decision between explore and exploit for this step [mandatory]
    def decision_explore_exploit(self, state:AgentState)->str:
        
        percentage_of_exploration = state['percentage_of_exploration']
        prior_estimation = state['prior_scores']
        posterior_estimation = state['posterior_scores']

        # confidence in best matches: prior and posterior estimations
        confidence = compute_confidence(prior_estimation, posterior_estimation)
        conservative_behavior = .5

        # decision based on exploration, confidence and behavior
        decision_threshold = conservative_behavior * percentage_of_exploration + (1 - conservative_behavior) * confidence

        # random event
        decision_event_value = random.random()
        if decision_event_value >= decision_threshold: 
            return "exploit"
        return "explore"

if __name__ == "__main__":
    system_prompt = (
        "You are a drone navigation assistant agent. "
        "You receive a 7D pose and image at each step, search previous observations, "
        "evaluate similarity, and decide to explore or exploit the environment. "
        "Use the prompt provided to guide decision-making."
    )
    user_prompt = input("Input the user prompt: \n\t")
    # user_prompt = "Find the bedroom."
    full_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
