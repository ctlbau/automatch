import pandas as pd
from .db_connect import connect, localauth
import json

import pandas as pd
import geopandas as gpd

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
                                        S.name AS shift,
                                        MAX(CASE WHEN DV.driver_id IS NOT NULL THEN TRUE ELSE FALSE END) AS is_matched
                                    FROM
                                        Drivers D
                                        LEFT JOIN Provinces P ON D.province_id = P.id
                                        LEFT JOIN Managers M ON D.manager_id = M.id
                                        LEFT JOIN Shifts S ON D.shift_id = S.id
                                        LEFT JOIN DriversVehicles DV ON D.kendra_id = DV.driver_id
                                    GROUP BY
                                        D.kendra_id, D.name, D.street, D.city, D.country, D.zip_code, D.lat, D.lng, P.name, M.name, S.name;""")
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
