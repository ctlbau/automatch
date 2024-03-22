import pandas as pd
from db.db_connect import connect, kndauth, localauth, companies
from sqlalchemy import text
import json
import geopandas as gpd

def fetch_centers():
    engine = connect(localauth)
    query = text("SELECT id, name FROM Centers;")
    centers_df = pd.read_sql(query, engine)
    return centers_df

def fetch_managers():
    engine = connect(localauth)
    query = text("SELECT id, name FROM Managers;")
    managers_df = pd.read_sql(query, engine)
    return managers_df

def fetch_shifts():
    engine = connect(localauth)
    query = text("SELECT id, name FROM Shifts;")
    shifts_df = pd.read_sql(query, engine)
    return shifts_df

def fetch_drivers_geojson():
    engine = connect(localauth)
    query = text("""SELECT
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
    drivers_df = pd.read_sql(query, engine)
    drivers_gdf = gpd.GeoDataFrame(drivers_df, geometry=gpd.points_from_xy(drivers_df.lng, drivers_df.lat)).set_crs(4326)
    drivers_gdf = drivers_gdf.drop(columns=['lat', 'lng'])
    drivers_geojson = json.loads(drivers_gdf.to_json())
    return drivers_geojson

import pandas as pd
import geopandas as gpd
from sqlalchemy import text

def fetch_drivers():
    engine = connect(localauth)
    query = text("""SELECT
                        match1.driver_id,
                        match1.driver_name,
                        match1.street,
                        match1.lat,
                        match1.lng,
                        match1.vehicle_id,
                        match1.manager,
                        match1.shift,
                        match1.center,
                        IF(COUNT(DISTINCT match2.driver_id) > 0, 1, 0) AS is_matched,
                        GROUP_CONCAT(DISTINCT match2.name ORDER BY match2.name SEPARATOR ', ') AS matched_with,
                        match1.exchange_location
                    FROM (
                        SELECT
                            D.kendra_id AS driver_id,
                            D.name AS driver_name,
                            D.street,
                            D.lat,
                            D.lng,
                            DV.vehicle_id,
                            DV.exchange_location_id,  -- Needed for joining with ExchangeLocations
                            EL.name AS exchange_location,  -- Joining with ExchangeLocations to get the name
                            M.name AS manager,
                            S.name AS shift,
                            C.name AS center
                        FROM
                            Drivers D
                            JOIN DriversVehicles DV ON D.kendra_id = DV.driver_id
                            JOIN Vehicles V ON DV.vehicle_id = V.kendra_id
                            LEFT JOIN ExchangeLocations EL ON DV.exchange_location_id = EL.id  -- LEFT JOIN to include drivers even if exchange_location_id is NULL
                            JOIN Managers M ON D.manager_id = M.id
                            JOIN Shifts S ON D.shift_id = S.id
                            JOIN Centers C ON V.center_id = C.id
                    ) AS match1
                    LEFT JOIN (
                        SELECT
                            D.kendra_id AS driver_id,
                            D.name,
                            DV.vehicle_id
                        FROM
                            Drivers D
                            JOIN DriversVehicles DV ON D.kendra_id = DV.driver_id
                    ) AS match2 ON match1.vehicle_id = match2.vehicle_id AND match1.driver_id != match2.driver_id
                    GROUP BY
                        match1.driver_id, match1.driver_name, match1.street, match1.lat, match1.lng, match1.vehicle_id, match1.manager, match1.shift, match1.center, match1.exchange_location
                    ORDER BY
                        match1.driver_id;""")
    drivers_df = pd.read_sql(query, engine)
    drivers_gdf = gpd.GeoDataFrame(drivers_df, geometry=gpd.points_from_xy(drivers_df.lng, drivers_df.lat), crs='EPSG:4326')
    drivers_list_dict = [
        {
            "coordinates": [driver.geometry.x, driver.geometry.y],
            "color": [255, 0, 0, 255],  # Example color: red
            "radius": 50,  # Example radius
            "name": driver["driver_name"],
            "street": driver["street"],
            "manager": driver["manager"],
            "shift": driver["shift"],
            "center": driver["center"],
            "is_matched": driver["is_matched"],
            "matched_with": driver["matched_with"],
            "exchange_location": driver["exchange_location"],  # Include exchange location in the dictionary
        } for index, driver in drivers_gdf.iterrows()
    ]
    return drivers_df, drivers_gdf, drivers_list_dict

