import networkx as nx 
import numpy as np

# load points from the truth database 
points = {
    1: [-0.87, -7.46, 1.25, -0.5776832276006791, -0.5776832276006791, -0.5766837756498129, -2.09],
    2: [-2.1, -7.45619, 1.24828, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841],
    3: [-4.82, -7.44772, 1.24449, 0.0006112608201322481, 0.7082067916052212, 0.7060047922531747, 3.13841],
    4: [-5.41, -7.4459, 1.24367, -0.5776830771686436, -0.5776830771686436, -0.5766840770351942, -2.089995307179586],
    5: [-5.41, -7.4459, 1.24367, 0.1865310645653143, 0.6956492407899829, 0.6937422401298994, 2.76978],
    6: [-6.09869, -8.6302, 1.24641, -0.281388164649127, -0.6793973975369346, -0.6776723965275819, -2.589625307179586],
    7: [-5.62511, -7.48164, 1.24352, -0.9999970711095111, 0.002260400160736421, 0.0008650800615156003, -1.5676853071795867],
    8: [-5.61966, -5.73164, 1.23808, 0.8634228050620333, 0.3566769194718126, 0.35676691945149297, 1.71347],
    9: [-5.61966, -5.73164, 1.23808, -0.575815941301038, 0.5794159409340522, 0.5768129411994033, -2.0952053071795866],
    10: [-5.61966, -5.73164, 1.23808, 0.9342146278813679, -0.2532738991153274, -0.25118789994622764, 1.63606],
    11: [-4.00606, -3.95156, 1.23476, -0.7731190327454575, 0.44972501904810364, 0.4472520189433597, -1.8230853071795865],
}

def get_index_from_points(point, points_dict=points):
    return list(points_dict.values()).index(point) +1

edges = [
    (1,2),
    (2,3),
    (2,4),
    (2,5),
    (2,7),
    (3,4),
    (3,5),
    (3,7),
    (4,5),
    (4,7),
    (5,6),
    (5,7),
    (7,8),
    (7,9),
    (7,10),
    (8,9),
    (8,10),
    (9,10),
    (10,11),
]

class SpatialAPI:
    def __init__(self, points=points, edges=edges):
        
        def check_integrity(name, container, expected_type, expected_width):
            if len(container) <= 0: raise IndexError(f"{name} should contain at least one element.")
            if not isinstance(container, expected_type): raise TypeError(f"{name} should be of type {expected_type} instead of {type(container)}.")
            width = -1
            try:
                if isinstance(container, (set, list, tuple)):
                    width = np.array(container).shape[-1]
                elif isinstance(container, dict):
                    elts = list(container.values())
                    width = np.array(elts).shape[-1]
            except ValueError as e:
                raise ValueError(f"{name} should contain elements with the same type and shape.")
            if width != expected_width: raise ValueError(f"{name} should contains elements of width {expected_width}")

        check_integrity("points", points, dict, 6)
        check_integrity("edges", edges, list, 2)
        
        points_set = set(points.keys())
        edges_set = set(np.array(edges).flatten())
        if points_set != edges_set:
            missing = []
            if points_set.difference(edges_set) != set():
                missing = [*missing, *list(points_set.difference(edges_set))]
            if edges_set.difference(points_set) != set():
                missing = [*missing, *list(edges_set.difference(points_set))]
            raise ValueError(f"The points {missing} are missing in either the points or the edges.")

        self._graph = nx.Graph()
        self._points = points 
        self._edges = edges 
        self._graph.add_nodes_from(points)
        self._graph.add_edges_from(edges)

    def existing_point(self, point):
        return point in self._points.values()

    def get_pose_point(self, pose_idx):
        return self._points.get(pose_idx)
    
    def get_pose_key(self, pose_value):
        return get_index_from_points(pose_value, self._points)
    
    def get_closest_points(self, source_point, excluded_points=[]):
        assert self.existing_point(source_point)
        assert all([self.existing_point(pt) for pt in excluded_points])

        # add source_point for safety
        excluded_points.append(source_point)

        # go to the index space for simpler computation
        set_all_points = set(self._points.keys())
        set_excluded_points = set([self.get_pose_key(p) for p in excluded_points])
        source_key = self.get_pose_key(source_point)
        
        # exclude the points from the total
        set_candidates_points = set_all_points.difference(set_excluded_points)

        # compute the shortest path for each candidate
        paths_idx = [self.get_shortest_path(source_key, candidate_pt, output_as_points=False) for candidate_pt in set_candidates_points]

        # get the closests points
        closests_idx = [p.pop() for p in paths_idx if len(p) == 1]
        closests_pts = [self.get_pose_point(i) for i in closests_idx]

        return closests_pts # shape: len(shortest_path_points), shortest_path, len(current_pose)

    def get_shortest_path(self, source, target, exclude_source_point=True, inputs_as_points=False, output_as_points=True):
        source_key = source if not inputs_as_points else self.get_pose_key(source)
        target_key = target if not inputs_as_points else self.get_pose_key(target)
        path = nx.shortest_path(self._graph, source_key, target_key)
        if exclude_source_point: 
            path = path[1:]
        if output_as_points:
            return [self.get_pose_point(p) for p in path]
        return path
    
    def filter_existing_points(self, request_list_points):
        return [point for point in request_list_points if point in self._points.values()]
    
    def get_percentage_of_exploration(self, explored_points):
        assert all([self.existing_point(pt) for pt in explored_points])
        
        existing_explored_points = self.filter_existing_points(explored_points)
        return len(existing_explored_points) / len(self._points)

if __name__ == "__main__":
    spatial_api = SpatialAPI()
    pose_idx = input("Input the index of the pose to move: \n\t")
    target_pose = spatial_api.get_pose_point(pose_idx)
    print(target_pose)