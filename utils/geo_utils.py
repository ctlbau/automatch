import os
import json
import requests as req
import pandas as pd
from shapely.geometry import shape, LineString
import polyline
import json
import urllib.parse
import re

MAPBOX_API_KEY = os.environ["MAPBOX_TOKEN"]
FIVE_MINUTES = 300
BASE_URL = "http://localhost:8989"

def calculate_driver_distances_and_paths(gdf):
    pathurl = f"{BASE_URL}/route"
    
    gdf["distance"] = None
    gdf["path"] = None
    
    errors = []
    
    for index, row in gdf.iterrows():
        if row["is_matched"]:
            # Extract the driver's coordinates from the geometry column
            driver_coords = row["geometry"]
            driver_lng, driver_lat = driver_coords.x, driver_coords.y        
            matched_driver_id = row["matched_driver_id"]
            
            matched_driver = gdf[gdf["driver_id"] == matched_driver_id]
            if not matched_driver.empty:
                matched_driver_coords = matched_driver["geometry"].values[0]
                matched_driver_lng, matched_driver_lat = matched_driver_coords.x, matched_driver_coords.y
                
                params = {
                    "point": [f"{driver_lat},{driver_lng}", f"{matched_driver_lat},{matched_driver_lng}"],
                    "profile": "car"
                }
                
                response = req.get(pathurl, params=params)
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
                    error_info = {
                        "driver_id": row["driver_id"],
                        "matched_driver_id": matched_driver_id,
                        "error_code": response.status_code,
                        "error_message": f"Failed to calculate route. Error: {response.status_code} - Please check the driver and matched driver locations.",
                        "suggested_action": "Verify the locations for both drivers and try again."
                    }
                    errors.append(error_info)
            else:
                error_info = {
                    "driver_id": row["driver_id"],
                    "matched_driver_id": matched_driver_id,
                    "error_message": "Matched driver not found - Please verify the matched driver ID.",
                    "error_code": "Matched driver not found",
                    "suggested_action": "Check the matched driver ID for accuracy and try again."
                }
                errors.append(error_info)
    
    error_df = pd.DataFrame(errors, columns=["driver_id", "matched_driver_id", "error_code", "error_message", "suggested_action"])
    
    return gdf, error_df


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

def geodecode_coordinates(lat, lon):
    """
    Convert latitude and longitude to a human-readable address using the Nominatim API.

    Parameters:
    - lat (float): Latitude of the location.
    - lon (float): Longitude of the location.

    Returns:
    - str: The closest address to the provided latitude and longitude, or an error message.
    """
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"

    response = req.get(url, headers={"User-Agent": "AuroPulse/1.0 (ctrebbau@pm.me)"})

    if response.status_code == 200:
        data = response.json()
        address = data.get("display_name")
        if address:
            return address
    else:
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
                continue 
            else:
                # Found common drivers between partitions i and j
                return False
    return True


################## Wailon API ##################

from dotenv import load_dotenv
thisdir = os.path.dirname(__file__)
parentdir = os.path.dirname(thisdir)
load_dotenv(os.path.join(parentdir, '.env'))

def get_session_id():
    token = os.environ.get('SHERLOG_TOKEN')
    if not token:
        raise ValueError("SHERLOG_TOKEN environment variable is not set.")

    login_url = "https://hst-api.wialon.com/wialon/ajax.html?svc=token/login"
    payload = {
        "params": json.dumps({
            "token": token
        })
    }

    try:
        response = req.get(login_url, params=payload)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            error_code = data['error']
            error_message = data.get('reason', 'Unknown error')
            raise ValueError(f"Error {error_code}: {error_message}")
        session_id = data.get('eid')
        if session_id is None:
            raise ValueError("Session ID not found in the response.")
        return session_id
    except req.exceptions.RequestException as e:
        raise ValueError(f"Error occurred while getting session ID: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error occurred while parsing response: {e}")

def lic_plate2sher_id_map():
    session_id = get_session_id()
    core_svc = "https://hst-api.wialon.com/wialon/ajax.html?svc=core/search_items&params="
    coreprefix = {
        "spec": {
            "itemsType": "avl_unit",
            "propName": "sys_id",
            "propValueMask": "*",
            "sortType": "sys_id",
            "propType": "list"
        },
        "force": 1,
        "flags": 1,
        "from": 0,
        "to": 0
    }
    coreprefix_json = json.dumps(coreprefix)
    coreprefix_escaped = urllib.parse.quote(coreprefix_json)
    url = core_svc + coreprefix_escaped + "&sid=" + session_id
    r = req.get(url)
    payload = json.loads(r.text)
    name2id = {}
    for i in range(len(payload["items"])):
        name = re.split(r"\W", payload["items"][i]["nm"])[0]
        name2id[name] = payload["items"][i]["id"]
    return name2id

def get_last_coordinates_by_plate(plate, plates2ids=lic_plate2sher_id_map()):
    session_id = get_session_id()
    if plate not in plates2ids:
        print(f"License plate '{plate}' not found in the database.")
        return None

    vehicle_id = plates2ids[plate]
    core_svc = "https://hst-api.wialon.com/wialon/ajax.html?svc=core/search_item&params="
    coreprefix = {
        "id": vehicle_id,
        "flags": 1025
    }
    coreprefix_json = json.dumps(coreprefix)
    coreprefix_escaped = urllib.parse.quote(coreprefix_json)
    url = core_svc + coreprefix_escaped + "&sid=" + session_id
    r = req.get(url)
    payload = json.loads(r.text)

    if "item" in payload and isinstance(payload["item"], dict):
        item = payload["item"]
        if "lmsg" in item and isinstance(item["lmsg"], dict):
            last_message = item["lmsg"]
            if "pos" in last_message and isinstance(last_message["pos"], dict):
                pos = last_message["pos"]
                if "y" in pos and "x" in pos:
                    coords = {
                        "lat": pos["y"],
                        "lng": pos["x"]
                    }
                    return coords

    print(f"Last known coordinates not found for license plate '{plate}'.")
    return None