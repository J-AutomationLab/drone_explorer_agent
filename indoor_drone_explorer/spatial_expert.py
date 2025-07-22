import networkx as nx 

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

def get_index_from_points(point):
    return list(points.values()).index(point) +1

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
        self._graph = nx.Graph()
        self._points = points 
        self._edges = edges 
        self._graph.add_nodes_from(points)
        self._graph.add_edges_from(edges)

    def get_pose_value(self, pose_idx):
        return self._points.get(pose_idx)
    
    def get_pose_key(self, pose_value):
        return get_index_from_points(pose_value)
    
    def get_neighbors(self, pose_idx):
        return list(self._graph.adj[pose_idx])

    def get_shortest_path(self, source_idx, target_idx):
        return nx.shortest_path(self._graph, source_idx, target_idx)

if __name__ == "__main__":
    spatial_api = SpatialAPI()
    pose_idx = input("Input the index of the pose to move: \n\t")
    target_pose = spatial_api.get_pose_value(pose_idx)
    print(target_pose)