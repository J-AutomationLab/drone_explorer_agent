# test_spatial_api.py
import pytest
from src import spatial_api

##### Fixtures #####

@pytest.fixture
def sample_points_edges():
    points = {x: [x]*6 for x in range(1,6)}
    edges = [(1,2), (1,3), (2,4), (3,5), (4,5)]
    return points, edges

@pytest.fixture
def sapi(sample_points_edges):
    points, edges = sample_points_edges
    return spatial_api.SpatialAPI(points.copy(), edges.copy())

##### Positive tests #####

def test_point_getters(sapi, sample_points_edges):
    points, _ = sample_points_edges
    key, point = 1, points[1]
    assert sapi.existing_point(point)
    assert not sapi.existing_point([float('inf')]*6)
    assert sapi.get_pose_point(key) == [key]*6
    assert sapi.get_pose_key(point) == key

def test_shortest_path(sapi):
    src_key, trgt_key = 1, 4
    assert sapi.get_shortest_path(src_key, trgt_key, exclude_source_point=False, output_as_points=False) == [1,2,4]
    assert sapi.get_shortest_path(src_key, trgt_key, output_as_points=False) == [2,4]
    assert sapi.get_shortest_path(src_key, trgt_key) == [[2]*6, [4]*6]
    assert sapi.get_shortest_path([src_key]*6, [trgt_key]*6, inputs_as_points=True, output_as_points=False) == [2,4]

def test_closest_points(sapi, sample_points_edges):
    points, _ = sample_points_edges
    src_pt = points[1]
    assert sapi.get_closest_points(src_pt) == [points[k] for k in [2,3]]
    assert sapi.get_closest_points(src_pt, excluded_points=[points[3]]) == [points[2]]
    assert sapi.get_closest_points(src_pt, [points[k] for k in [2,3]]) == []

def test_percentage_of_exploration(sapi, sample_points_edges):
    points, _ = sample_points_edges
    explored_points = [points[k] for k in [1,2,4]]
    assert sapi.get_percentage_of_exploration(explored_points) == 0.6

##### Negative tests #####

def test_init_invalid_points_edges():
    points = {x: [x]*6 for x in range(1,6)}
    edges = [(1,2), (1,3), (2,4), (3,5), (4,5)]

    # points empty
    with pytest.raises(IndexError):
        spatial_api.SpatialAPI({}, edges.copy())

    # point not a list
    broken_points = points.copy()
    broken_points[1] = 0
    with pytest.raises(ValueError):
        spatial_api.SpatialAPI(broken_points, edges.copy())

    # point with wrong length
    broken_points[1] = [1]*5
    with pytest.raises(ValueError):
        spatial_api.SpatialAPI(broken_points, edges.copy())

    # edges empty
    with pytest.raises(IndexError):
        spatial_api.SpatialAPI(points.copy(), [])

    # negative value in edge
    broken_edges = edges + [(1, -1)]
    with pytest.raises(IndexError):
        spatial_api.SpatialAPI(points.copy(), [])

    # point in edge not in points
    broken_edges = edges + [(5, 99)] # 99 missing
    with pytest.raises(ValueError):
        spatial_api.SpatialAPI(points.copy(), broken_edges)

    # one edge malformed
    broken_edges = edges + [(1,3,5)]
    with pytest.raises(ValueError):
        spatial_api.SpatialAPI(points.copy(), broken_edges)

import torch 
def test_gpu_available():
    assert torch.cuda.is_available()