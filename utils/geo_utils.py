import os
import json
import requests as req
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape

GRAPHHOPPER_URL = "http://localhost:8989/isochrone"
FIVE_MINUTES = 300
MAPBOX_API_KEY = os.environ["MAPBOX_TOKEN"]
BASE_URL = "http://localhost:8989/isochrone"


def geoencode_address(address: str, province: str, postal_code: str):
    """ Get coordinates from Nominatim API, assuming the address is in Spain """
    address += f", {province}, {postal_code}, España"
    headers = {'User-Agent': 'AuroPulse/1.0 (ctrebbau@pm.me)'}
    params = {'q': address, 'format': 'json'}
    response = req.get('https://nominatim.openstreetmap.org/search', headers=headers, params=params)
    try:
        data = response.json()
        if not data:
            return None
        return data[0]['lat'], data[0]['lon']
    except json.JSONDecodeError:
        print(f'Failed to decode JSON from response. Status Code: {response.status_code}, Response Text: {response.text}')
        return None

def calculate_isochrones(lat: float, lon: float, times: list) -> dict:
    """Fetch isochrones for specified times."""
    max_time = max(times)  # The furthest time limit
    buckets = len(times)  # The number of isochrones to generate
    params = {
        "point": f"{lat},{lon}",
        "time_limit": max_time * 60,  # Convert to seconds
        "profile": "car",
        "buckets": buckets
    }
    response = req.get(GRAPHHOPPER_URL, params=params)
    if response.status_code == 200:
        isochrones_features = response.json().get("polygons")
        if isochrones_features is not None:
            isochrones_geojson = dict(type="FeatureCollection", features=isochrones_features)
            # isochrones_gdf = gpd.GeoDataFrame.from_features(isochrones_geojson['features']).set_crs(4326)
            return isochrones_geojson
        else:
            print("No features found in the response.")
            return None
    else:
        print(f"Failed to fetch isochrones: {response.status_code}")
        return None



def extract_geometries_from_feature_collection(feature_collection):
    """
    Extract geometries from a GeoJSON FeatureCollection.

    :param feature_collection: A GeoJSON FeatureCollection.
    :return: A list of geometries extracted from the FeatureCollection.
    """
    geometries = [feature["geometry"] for feature in feature_collection["features"]]
    return geometries

def partition_drivers_by_isochrones(drivers_gdf, isochrones):
    """
    Partition drivers based on whether they fall within nested isochrones.
    
    :param drivers_gdf: GeoDataFrame of drivers
    :param isochrones: List of polygons (isochrones), ordered from innermost to outermost
    :return: List of GeoDataFrames, each corresponding to drivers within a specific isochrone, 
             and the last one containing drivers outside all isochrones.
    """
    partitioned_drivers = []
    remaining_drivers = drivers_gdf.copy()
    # make remaining_drivers unique
    remaining_drivers = remaining_drivers.drop_duplicates(subset=['driver_id'])
    isochrone_geoms = extract_geometries_from_feature_collection(isochrones)
    for isochrone in isochrone_geoms:
        isochrone_geom = shape(isochrone)
        within_isochrone = remaining_drivers[remaining_drivers.geometry.within(isochrone_geom)]
        partitioned_drivers.append(within_isochrone)
        remaining_drivers = remaining_drivers[~remaining_drivers.index.isin(within_isochrone.index)]
    
    partitioned_drivers.append(remaining_drivers)  # Drivers outside all isochrones
    
    return partitioned_drivers

def extract_coords_from_encompassing_isochrone(geojson):
    largest_isochrone = geojson['features'][-1]
    polygon = shape(largest_isochrone['geometry'])
    exterior_coords = list(polygon.exterior.coords)
    return exterior_coords

def check_partitions_intersection(partitioned_drivers):
    """
    Check that the intersection of every pairwise partition is empty.
    
    :param partitioned_drivers: List of GeoDataFrames, each corresponding to drivers within a specific isochrone, 
                                and the last one containing drivers outside all isochrones.
    :return: True if all intersections are empty, False otherwise.
    """
    num_partitions = len(partitioned_drivers)
    for i in range(num_partitions):
        for j in range(i + 1, num_partitions):
            # Check if there is any common index between partition i and partition j
            if not partitioned_drivers[i].index.isin(partitioned_drivers[j].index).any():
                continue  # No common drivers, check the next pair
            else:
                # Found common drivers between partitions i and j
                return False
    return True
