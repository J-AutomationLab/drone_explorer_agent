import random 
import time 
from typing import TypedDict, Dict, List

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

def compute_similarity_between_2_texts(txt1, txt2):
    embeddings = [txt_similarity_model.encode(txt, convert_to_tensor=True) for txt in [txt1,txt2]]
    return float(util.cos_sim(*embeddings))

def get_best_matches_images_description_with_prompt(data, prompt, n_best):
    # compute similarity 
    for k, v in data.items():
        prior_text = v['blip']
        prior_scores = []
        for token in prompt + [prompt]:
            token_scores = [compute_similarity_between_2_texts(s, token) for s in prior_text]
            prior_scores.append(token_scores)
        data[k]['prior_score'] = np.max(prior_scores)
    
    # get the best matches 
    best_matches = sorted(data.items(), key=lambda x: x[1]['prior_score'], reverse=True) # tuple 

    return best_matches[:n_best]

def query_clip(image_path, prompts_per_image):
    image = Image.open(image_path).convert("RGB")
    inputs = clip_processor(text=prompts_per_image, images=image, return_tensors='pt', padding=True)
    with torch.no_grad():
        outputs = clip_model(**inputs)
    logits = outputs.logits_per_image 
    probs = logits.softmax(dim=1)

    return probs.cpu().numpy() 

def compute_confidence(prior, posterior):
    (prior + 3 * posterior) / 4

##### memory state #####
class AgentState(TypedDict):
    prompt: str
    prior_score: float 
    posterior_score: float 
    percentage_of_exploration: float 
    current_pose7d: List[float]
    decision: str 
    target_pose7d: List[float]

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
        builder.add_node('estimate_memory', self.estimate_memory) 
        builder.add_node('decision_explore_exploit', self.decision_explore_exploit)
        builder.add_node('explore', self.explore)
        builder.add_node('exploit', self.exploit)
        builder.add_node('move', self.move)

        builder.set_entry_point('load_memory')
        builder.add_edge('explore', 'move')
        builder.add_edge('exploit', 'move')
        builder.add_edge('move', END)
        builder.add_conditional_edges('decision_explore_exploit', self.decision_explore_exploit, {'explore': self.explore, 'exploit': self.exploit})

        return builder.compile()
    
    def run(self, user_prompt):
        initial_state = AgentState(
            prompt=user_prompt,
            current_pose7d=self._hardware_operator.current_pose, 
            target_pose7d=List[float],
            decision=str, 
            prior_score=float, 
            posterior_score=float, 
            percentage_of_exploration=float,
        )

        results = self._agent.compile(initial_state)['decision']
        return results

    # load the database and filter the best matches [mandatory]
    def load_memory(self, state:AgentState)->AgentState:
        self._memory = load_data(DATABASE_MEMORY_PATH, ['blip'])
        return state 
    
    # estimate the similarity between the memory and the prompt
    def estimate_memory(self, state:AgentState)->AgentState:
        prompt = state['prompt']
        memory = self._memory
        all_poses = [v['pose7d'] for v in memory.values()]
        
        best_blip_matches = get_best_matches_images_description_with_prompt(memory, prompt, self.N_BEST_SIMILARITY_MATCHES)
        self._memory = dict(best_blip_matches).copy()
        state['prior_score'] = [x[1]['prior_score'] for x in best_blip_matches]

        percentage_of_exploration = self._spatial_api.get_percentage_of_exploration(all_poses)
        state['percentage_of_exploration'] = percentage_of_exploration

        clip_matches = [query_clip(image_path, prompts) for image_path, prompts in best_blip_matches]
        for k, score in clip_matches:
            self._memory[k]['posterior_score'] = score 
        state['posterior_score'] = np.max([x[1] for x in clip_matches])

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
        target_pose = list(self._memory.values())[target_index]
        state['target_pose7d'] = target_pose

        return state

    def move(self, state:AgentState) -> AgentState:
        path_to_target = self._spatial_api.get_shortest_path(state['current_pose7d'], state['target_pose7d'])
        for path in path_to_target:
            step_pose = self._spatial_api.get_pose_value(path)
            self._hardware_operator.send_cmd(step_pose)
            time.sleep(1) # simulate the time to arrive to step pose
        return state 

    # compute the decision between explore and exploit for this step [mandatory]
    def decision_explore_exploit(self, state:AgentState)->AgentState:
        
        percentage_of_exploration = state['percentage_of_exploration']
        prior_estimation = state['prior_score']
        posterior_estimation = state['posterior_score']

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
