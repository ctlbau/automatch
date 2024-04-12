import os
import json
import requests as req
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
from shapely.geometry import LineString
import polyline

MAPBOX_API_KEY = os.environ["MAPBOX_TOKEN"]
FIVE_MINUTES = 300
BASE_URL = "http://localhost:8989"

def calculate_driver_distances_and_paths(gdf):
    pathurl = f"{BASE_URL}/route"
    # print(f"Calculating distances and paths for {len(gdf)} drivers...")
    
    # Create new columns to store the calculated distances and paths
    gdf["distance"] = None
    gdf["path"] = None
    
    # Create a list to store the error information
    errors = []
    
    # Iterate over each row in the GeoDataFrame
    for index, row in gdf.iterrows():
        # Check if the driver is matched
        if row["is_matched"]:
            # Extract the driver's coordinates from the geometry column
            driver_coords = row["geometry"]
            driver_lng, driver_lat = driver_coords.x, driver_coords.y        
            matched_driver_id = row["matched_driver_id"]
            
            # Find the matched driver's coordinates
            matched_driver = gdf[gdf["driver_id"] == matched_driver_id]
            if not matched_driver.empty:
                matched_driver_coords = matched_driver["geometry"].values[0]
                matched_driver_lng, matched_driver_lat = matched_driver_coords.x, matched_driver_coords.y
                
                # Set the query parameters for the API request
                params = {
                    "point": [f"{driver_lat},{driver_lng}", f"{matched_driver_lat},{matched_driver_lng}"],
                    "profile": "car"
                }
                
                # Send the GET request to the API
                response = req.get(pathurl, params=params)
                
                # Check if the request was successful
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract the distance from the response
                    distance = data["paths"][0]["distance"]
                    
                    # Extract the encoded path points from the response
                    encoded_points = data["paths"][0]["points"]
                    
                    # Decode the encoded path points
                    decoded_points = polyline.decode(encoded_points)
                    
                    # Check if the decoded points array has at least two points
                    if len(decoded_points) >= 2:
                        # Create a LineString geometry from the decoded path points
                        path_geometry = LineString(decoded_points)
                    else:
                        # Set the path geometry to None if the decoded points array is invalid
                        path_geometry = None
                    
                    # Store the calculated distance and path in the GeoDataFrame
                    gdf.at[index, "distance"] = distance
                    gdf.at[index, "path"] = path_geometry
                else:
                    # Store the error information
                    error_info = {
                        "driver_id": row["driver_id"],
                        "matched_driver_id": matched_driver_id,
                        "error_code": response.status_code,
                        "error_message": f"Failed to calculate route. Error: {response.status_code} - Please check the driver and matched driver locations.",
                        "suggested_action": "Verify the locations for both drivers and try again."
                    }
                    errors.append(error_info)
            else:
                # Store the error information for unmatched driver
                error_info = {
                    "driver_id": row["driver_id"],
                    "matched_driver_id": matched_driver_id,
                    "error_message": "Matched driver not found - Please verify the matched driver ID.",
                    "error_code": "Matched driver not found",
                    "suggested_action": "Check the matched driver ID for accuracy and try again."
                }
                errors.append(error_info)
    
    # Create a DataFrame from the error information with clear columns
    error_df = pd.DataFrame(errors, columns=["driver_id", "matched_driver_id", "error_code", "error_message", "suggested_action"])
    
    return gdf, error_df

def get_manager_stats(df):
    # Group by manager and calculate statistics
    manager_stats = df.groupby('manager').agg(
        total_drivers=('driver_id', 'count'),
        matched_drivers=('is_matched', 'sum'),
        unmatched_drivers=('is_matched', lambda x: (x == 0).sum()),
        avg_distance=('distance', lambda x: round(x.mean() / 1000, 2)),
        min_distance=('distance', lambda x: round(x.min() / 1000, 2)),
        max_distance=('distance', lambda x: round(x.max() / 1000, 2)),
        cambio_fuera_count=('exchange_location', lambda x: (x == 'Cambio fuera').sum()),
        cambio_fuera_matched_count=('is_matched', lambda x: x[df['exchange_location'] == 'Cambio fuera'].sum()),
        cambio_fuera_avg_distance=('distance', lambda x: round(x[df['exchange_location'] == 'Cambio fuera'].mean() / 1000, 2)),
        cambio_fuera_min_distance=('distance', lambda x: round(x[df['exchange_location'] == 'Cambio fuera'].min() / 1000, 2)),
        cambio_fuera_max_distance=('distance', lambda x: round(x[df['exchange_location'] == 'Cambio fuera'].max() / 1000, 2))
    ).reset_index()

    manager_stats['matched_percentage'] = round(manager_stats['matched_drivers'] / manager_stats['total_drivers'] * 100, 2)
    manager_stats['cambio_fuera_percentage'] = round(manager_stats['cambio_fuera_count'] / manager_stats['total_drivers'] * 100, 2)
    manager_stats['cambio_fuera_matched_percentage'] = round(manager_stats['cambio_fuera_matched_count'] / manager_stats['cambio_fuera_count'] * 100, 2)

    # Rename columns starting with "cambio_fuera" to "hot_"
    manager_stats = manager_stats.rename(columns=lambda x: x.replace('cambio_fuera', 'hot') if x.startswith('cambio_fuera') else x)

    # Reorder columns
    manager_stats = manager_stats[[
        'manager', 'total_drivers', 'matched_drivers', 'unmatched_drivers', 'matched_percentage',
        'avg_distance', 'min_distance', 'max_distance',
        'hot_count', 'hot_percentage', 'hot_matched_count', 'hot_matched_percentage',
        'hot_avg_distance', 'hot_min_distance', 'hot_max_distance'
    ]]

    return manager_stats




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
    isourl = f"{BASE_URL}/isochrone"
    max_time = max(times)  # The furthest time limit
    buckets = len(times)  # The number of isochrones to generate
    params = {
        "point": f"{lat},{lon}",
        "time_limit": max_time * 60,  # Convert to seconds
        "profile": "car",
        "buckets": buckets
    }
    response = req.get(isourl, params=params)
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
