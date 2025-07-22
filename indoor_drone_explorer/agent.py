from typing import TypedDict, Dict, List

from langgraph.graph import StateGraph, END
from sentence_transformers import SentenceTransformer, util

from hardware_operator import HWOperator, load_data, DATABASE_MEMORY_PATH
from spatial_expert import SpatialAPI

##### models #####

txt_similarity_model = SentenceTransformer("all-MiniLM-L6-v2")

##### utils function #####

def compute_similarity_between_2_texts(txt1, txt2):
    embeddings = [txt_similarity_model.encode(txt, convert_to_tensor=True) for txt in [txt1,txt2]]
    return float(util.cos_sim(*embeddings))

##### memory state #####
class AgentState(TypedDict):
    prompt: str
    relevant_memory: Dict[str, List[float] | List[str] | str]
    current_pose7d: List[float]
    target_pose7d: List[float]

##### agent ##### 
class Agent:

    N_BEST_SIMILARITY_MATCHES = 3

    def __init__(self):
        self._hardware_operator = HWOperator()
        self._spatial_api = SpatialAPI()
        self._agent = self._build()

    def _build(self):
        builder = StateGraph(AgentState)
        builder.add_node('load_memory', self.load_memory)
        builder.add_node('compute_clip', self.compute_clip)
        builder.add_node('decision', self.compute_clip)
        builder.add_node('explore', self.compute_clip)
        builder.add_node('exploit', self.compute_clip)

        builder.set_entry_point('load_memory')
        builder.add_edge('decision', END)

        return builder.compile()
    
    def run(self, user_prompt):
        initial_state = AgentState(
            prompt=user_prompt,
            relevant_memory=Dict[str, List[float] | List[str] | str],
            current_pose7d=List[float], 
            target_pose7d=List[float],
        )

        results = self._agent.compile(initial_state)['decision']
        return results

    # load the database and filter the best matches [mandatory]
    def load_memory(self, state:AgentState)->AgentState:
        # load
        memory = load_data(DATABASE_MEMORY_PATH, ['blip'])
        prompt = state['prompt']

        # compute similarity
        for k, v in memory.items():
            prior_description = v['blip']
            similarities = [compute_similarity_between_2_texts(s, prompt) for s in prior_description]
            total_similarity = sum(similarities)/len(similarities)
            memory[k]['score'] = total_similarity
        
        # get the best matches 
        best_matches = dict(sorted(memory.items(), key=lambda x: x[1]['score'], reverse=True))[:self.N_BEST_SIMILARITY_MATCHES]

        # write
        state['relevant_memory'] = best_matches
        return state 
    
    # compute clip to get a better estimate [optional]
    def compute_clip(self, state:AgentState) ->AgentState:
        return state
    
    # explore the environment: try to find a better match [optional]
    def explore(self, state:AgentState)->AgentState:
        return state

    # exploit the memory: go the best registered match [optional]
    def exploit(self, state:AgentState)->AgentState:
        return state

    # compute the decision between explore and exploit for this step [mandatory]
    def decision(self, state:AgentState)->AgentState:
        return state

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
