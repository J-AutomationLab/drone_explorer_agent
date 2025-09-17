import unittest 
from src import spatial_api

class TestSpatialAPIPositivePath(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.points = {x: [x] * 6 for x in range(1,6,1)}
        cls.edges = [(1,2), (1,3), (2,4), (3,5), (4,5)]
        cls.sapi = spatial_api.SpatialAPI(cls.points.copy(), cls.edges.copy())
    
    def test_point_getters(self):
        key, point = 1, self.points[1]
        self.assertTrue(self.sapi.existing_point(point))
        self.assertFalse(self.sapi.existing_point([float('inf')]*6))
        self.assertEqual(self.sapi.get_pose_point(key), [key]*6)
        self.assertEqual(self.sapi.get_pose_key(point), key)

    def test_shortest_path(self):
        src_key, trgt_key = 1, 4 
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key, exclude_source_point=False, output_as_points=False), [1,2,4])
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key, output_as_points=False), [2,4])
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key), [[2]*6, [4]*6])
        self.assertEqual(self.sapi.get_shortest_path([src_key]*6, [trgt_key]*6, inputs_as_points=True, output_as_points=False), [2,4])

    def test_closest_path(self):
        src_pt = self.points[1]
        self.assertEqual(self.sapi.get_closest_points(src_pt), [self.points[k] for k in [2,3]])
        self.assertEqual(self.sapi.get_closest_points(src_pt, excluded_points=[self.points[3]]), [self.points[2]])
        self.assertEqual(self.sapi.get_closest_points(src_pt, [self.points[k] for k in [2,3]]), [])

    def test_percentage_of_exploration(self):
        explored_points = [self.points[k] for k in [1,2,4]]
        self.assertEqual(self.sapi.get_percentage_of_exploration(explored_points), .6)

class TestSpatialAPINegativePaths(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.points = {x: [x] * 6 for x in range(1,6,1)}
        cls.edges = [(1,2), (1,3), (2,4), (3,5), (4,5)]
        cls.sapi = spatial_api.SpatialAPI(cls.points.copy(), cls.edges.copy())

    def test_init(self):
        broken_points = self.points.copy()

        # points is empty 
        broken_points = {}
        with self.assertRaises(IndexError) as e:
            spatial_api.SpatialAPI(broken_points, self.edges.copy())

        # one point is not a list of float
        broken_points[1] = 0
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(broken_points, self.edges.copy())
        
        # one point does not have the same size than the other points
        broken_points[1] = [1] * 5
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(broken_points, self.edges.copy())
        
        # one point is nested in a container
        broken_points[1] = [[1] * 6]
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(broken_points, self.edges.copy())
        
        # edges is empty
        broken_edges = []
        with self.assertRaises(IndexError) as e:
            spatial_api.SpatialAPI(self.points, broken_edges)
        
        # one point does not exist in points
        broken_edges = [(1,2), (1,3), (2,4), (3,5), (4,5), (5,6)]
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(self.points, broken_edges)
        
        # one point is not in the edge from the others
        broken_edges = [(1,2), (1,3), (2,4)]
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(self.points, broken_edges)
        
        # one edge has a bad format
        broken_edges = [(1,2), (1,3), (2,4), (1,3,5), (4,5), (5,6)]
        with self.assertRaises(ValueError) as e:
            spatial_api.SpatialAPI(self.points, broken_edges)

    def test_point_getters(self):
        key, point = 1, self.points[1]
        self.assertTrue(self.sapi.existing_point(point))
        self.assertFalse(self.sapi.existing_point([float('inf')]*6))
        self.assertEqual(self.sapi.get_pose_point(key), [key]*6)
        self.assertEqual(self.sapi.get_pose_key(point), key)

    def test_shortest_path(self):
        src_key, trgt_key = 1, 4 
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key, exclude_source_point=False, output_as_points=False), [1,2,4])
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key, output_as_points=False), [2,4])
        self.assertEqual(self.sapi.get_shortest_path(src_key, trgt_key), [[2]*6, [4]*6])
        self.assertEqual(self.sapi.get_shortest_path([src_key]*6, [trgt_key]*6, inputs_as_points=True, output_as_points=False), [2,4])

    def test_closest_path(self):
        src_pt = self.points[1]
        self.assertEqual(self.sapi.get_closest_points(src_pt), [self.points[k] for k in [2,3]])
        self.assertEqual(self.sapi.get_closest_points(src_pt, excluded_points=[self.points[3]]), [self.points[2]])
        self.assertEqual(self.sapi.get_closest_points(src_pt, [self.points[k] for k in [2,3]]), [])

    def test_percentage_of_exploration(self):
        explored_points = [self.points[k] for k in [1,2,4]]
        self.assertEqual(self.sapi.get_percentage_of_exploration(explored_points), .6)
 