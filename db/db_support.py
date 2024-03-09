import pandas as pd
from .db_connect import connect, localauth
import json

import pandas as pd
import geopandas as gpd

def unmatch_drivers(candidate_id, matched_driver_id):
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            # Find vehicle IDs shared by both drivers
            local_cursor.execute("""
                SELECT dv1.vehicle_id
                FROM DriversVehicles dv1
                JOIN DriversVehicles dv2 ON dv1.vehicle_id = dv2.vehicle_id
                WHERE dv1.driver_id = %s AND dv2.driver_id = %s;
            """, (candidate_id, matched_driver_id))
            shared_vehicle_ids = local_cursor.fetchall()

            # For each shared vehicle, remove the link between the vehicle and each driver
            for vehicle_id in shared_vehicle_ids:
                local_cursor.execute("""
                    DELETE FROM DriversVehicles
                    WHERE (driver_id = %s OR driver_id = %s) AND vehicle_id = %s;
                """, (candidate_id, matched_driver_id, vehicle_id[0]))

            local_conn.commit()  # Commit the changes to the database


def fetch_drivers_matches(driver_ids):
    if driver_ids is None:
        return []
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.execute("""
                SELECT DISTINCT
                    d1.kendra_id AS candidate_id,
                    d1.name AS candidate_name,
                    s1.name AS candidate_shift,
                    m1.name AS candidate_manager,
                    d2.kendra_id AS matched_driver_id,
                    d2.name AS matched_driver_name,
                    s2.name AS matched_driver_shift,
                    m2.name AS matched_driver_manager,
                    v.plate AS matched_driver_plate
                FROM
                    Drivers d1
                    LEFT JOIN DriversVehicles dv1 ON d1.kendra_id = dv1.driver_id
                    LEFT JOIN DriversVehicles dv2 ON dv1.vehicle_id = dv2.vehicle_id
                        AND dv1.driver_id != dv2.driver_id
                    LEFT JOIN Drivers d2 ON dv2.driver_id = d2.kendra_id
                    LEFT JOIN Shifts s1 ON d1.shift_id = s1.id
                    LEFT JOIN Vehicles v ON dv1.vehicle_id = v.kendra_id
                    LEFT JOIN Managers m1 ON d1.manager_id = m1.id
                    LEFT JOIN Shifts s2 ON d2.shift_id = s2.id
                    LEFT JOIN Managers m2 ON d2.manager_id = m2.id
                WHERE
                    d1.kendra_id IN %s;
            """, (tuple(driver_ids),))
            driver_matches = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            driver_matches_df = pd.DataFrame(driver_matches, columns=columns)
            
            candidates = []
            grouped = driver_matches_df.groupby('candidate_id')
            for cid, group in grouped:
                candidate_row = group.iloc[0]
                candidate_dict = {
                    "id": cid,
                    "name": candidate_row['candidate_name'],
                    "shift": candidate_row['candidate_shift'],
                    "manager": candidate_row['candidate_manager'],
                    "matched_drivers": []
                }
                # Only add matched drivers if they exist
                matched_drivers = group[group['matched_driver_id'].notna()]
                for _, row in matched_drivers.iterrows():
                    matched_driver_dict = {
                        "id": row['matched_driver_id'],
                        "name": row['matched_driver_name'],
                        "shift": row['matched_driver_shift'],
                        "manager": row['matched_driver_manager'],
                        "vehicle": row['matched_driver_plate']
                    }
                    candidate_dict["matched_drivers"].append(matched_driver_dict)
                
                candidates.append(candidate_dict)
            return candidates


def fetch_managers():
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.execute("""SELECT id, name FROM Managers;""")
            managers = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            managers = pd.DataFrame(managers, columns=columns)
    return managers

def fetch_shifts():
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.execute("""SELECT id, name FROM Shifts;""")
            shifts = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            shifts = pd.DataFrame(shifts, columns=columns)
    return shifts

def fetch_drivers_geojson():
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.execute("""SELECT
                                    D.kendra_id,
                                    D.name AS name,
                                    D.street,
                                    D.city,
                                    D.country,
                                    D.zip_code,
                                    D.lat,
                                    D.lng,
                                    P.name AS province,
                                    M.name AS manager,
                                    S.name AS shift
                                FROM
                                    Drivers D
                                    LEFT JOIN Provinces P ON D.province_id = P.id
                                    LEFT JOIN Managers M ON D.manager_id = M.id
                                    LEFT JOIN Shifts S ON D.shift_id = S.id;""")
            drivers = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            drivers = pd.DataFrame(drivers, columns=columns)
            drivers = gpd.GeoDataFrame(drivers, geometry=gpd.points_from_xy(drivers.lng, drivers.lat)).set_crs(4326)
            drivers = drivers.drop(columns=['lat', 'lng'])
            drivers = json.loads(drivers.to_json())
    return drivers

def fetch_drivers():
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.execute("""SELECT
                                    D.kendra_id,
                                    D.name AS name,
                                    D.street,
                                    D.city,
                                    D.country,
                                    D.zip_code,
                                    D.lat,
                                    D.lng,
                                    P.name AS province,
                                    M.name AS manager,
                                    S.name AS shift
                                FROM
                                    Drivers D
                                    LEFT JOIN Provinces P ON D.province_id = P.id
                                    LEFT JOIN Managers M ON D.manager_id = M.id
                                    LEFT JOIN Shifts S ON D.shift_id = S.id;""")
            drivers = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            drivers_df = pd.DataFrame(drivers, columns=columns)
            # Convert DataFrame to GeoDataFrame
            drivers_gdf = gpd.GeoDataFrame(drivers_df, geometry=gpd.points_from_xy(drivers_df.lng, drivers_df.lat))
            drivers_gdf.set_crs(epsg=4326, inplace=True)
            # Convert to a list of dictionaries suitable for ScatterplotLayer
            drivers_list_dict = [
                {
                    "coordinates": [driver.geometry.x, driver.geometry.y],
                    "color": [255, 0, 0, 255],  # Example color: red
                    "radius": 50,  # Example radius
                    "name": driver["name"],
                    "street": driver["street"],
                    "manager": driver["manager"],
                    "shift": driver["shift"]
                } for index, driver in drivers_gdf.iterrows()
            ]
            
    return drivers_df, drivers_gdf, drivers_list_dict

# def fetch_drivers():
#     query = """
#     SELECT 
#         D.kendra_id,
#         D.name AS driver_name,
#         D.street,
#         D.city,
#         D.country,
#         D.zip_code,
#         D.lat,
#         D.lng,
#         P.name AS province_name,
#         M.name AS manager_name,
#         S.name AS shift_name
#     FROM Drivers D
#     LEFT JOIN Provinces P ON D.province_id = P.id
#     LEFT JOIN Managers M ON D.manager_id = M.id
#     LEFT JOIN Shifts S ON D.shift_id = S.id;
#     """
#     with connect(localauth) as local_conn:
#         with local_conn.cursor() as local_cursor:
#             local_cursor.execute(query)
#             drivers = local_cursor.fetchall()
#             columns = [desc[0] for desc in local_cursor.description]
#             drivers = pd.DataFrame(drivers, columns=columns)
#     return drivers
