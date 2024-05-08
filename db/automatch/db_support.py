import os
import pandas as pd
import geopandas as gpd
import numpy as np
from sqlalchemy import text
from db.db_connect import localauth_dev, localauth_stg, localauth_prod, connect

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    database = localauth_stg
elif app_env == 'dev':
    database = localauth_dev
else:
    database = localauth_prod


def fetch_exchange_locations():
    exchange_locations = ['Campa de Auro', 'Cambio fuera', 'Parking Reyes Magos', 'Parking Marqués de Urquijo']
    engine = connect(database)
    query = text("SELECT id, name FROM ExchangeLocations;")
    exchange_locations_df = pd.read_sql(query, engine)
    exchange_locations_df = exchange_locations_df.sort_values(by='name')
    exchange_locations_df = exchange_locations_df[exchange_locations_df["name"].isin(exchange_locations)]
    return exchange_locations_df

def fetch_centers():
    engine = connect(database)
    query = text("SELECT id, name FROM Centers;")
    centers_df = pd.read_sql(query, engine)
    centers_df = centers_df.sort_values(by='name')
    return centers_df

def fetch_managers():
    engine = connect(database)
    query = text("SELECT id, name FROM Managers;")
    managers_df = pd.read_sql(query, engine)
    managers_df = managers_df.sort_values(by='name')
    return managers_df

def fetch_shifts():
    shifts = ["L-J", "L-J (40h)", "Mañana", "Tarde", "TP-L-V", "TP-V-D"]
    engine = connect(database)
    query = text("SELECT id, name FROM Shifts;")
    shifts_df = pd.read_sql(query, engine)
    shifts_df = shifts_df[shifts_df["name"].isin(shifts)]
    shifts_df = shifts_df.sort_values(by='name')
    return shifts_df

def fetch_provinces():
    provinces = ["Madrid", "Málaga", "Barcelona", "Valencia", "Sevilla"]
    engine = connect(database)
    query = text("SELECT id, name FROM Provinces;")
    provinces_df = pd.read_sql(query, engine)
    provinces_df = provinces_df[provinces_df["name"].isin(provinces)]
    provinces_df = provinces_df.sort_values(by='name')
    return provinces_df

def fetch_drivers(province_ids):
    engine = connect(database)
    query = text("""
                SELECT 
                match1.driver_id, 
                match1.driver, 
                match1.street, 
                match1.lat, 
                match1.lng, 
                match1.vehicle_id, 
                match1.manager, 
                match1.shift, 
                match1.center, 
                match1.province, 
                IF(COUNT(DISTINCT match2.driver_id) > 0, 1, 0) AS is_matched, 
                GROUP_CONCAT(DISTINCT match2.name ORDER BY match2.name SEPARATOR ', ') AS matched_with, 
                match2.driver_id AS matched_driver_id, 
                match1.exchange_location 
                FROM (
                SELECT 
                D.kendra_id AS driver_id, 
                D.name AS driver, 
                D.street, 
                D.lat, 
                D.lng, 
                DV.vehicle_id, 
                DV.exchange_location_id, 
                EL.name AS exchange_location, 
                P.name AS province, 
                M.name AS manager, 
                S.name AS shift, 
                C.name AS center
                FROM Drivers D
                JOIN DriversVehiclesExchangeLocations DV ON D.kendra_id = DV.driver_id
                JOIN Vehicles V ON DV.vehicle_id = V.kendra_id
                LEFT JOIN ExchangeLocations EL ON DV.exchange_location_id = EL.id
                LEFT JOIN Provinces P ON D.province_id = P.id
                JOIN Managers M ON D.manager_id = M.id
                JOIN Shifts S ON D.shift_id = S.id
                JOIN Centers C ON V.center_id = C.id
                WHERE D.province_id IN :province_ids
                AND D.lat IS NOT NULL
                AND D.lng IS NOT NULL
                ) AS match1
                LEFT JOIN (
                SELECT 
                D.kendra_id AS driver_id, 
                D.name, 
                DV.vehicle_id
                FROM Drivers D
                JOIN DriversVehiclesExchangeLocations DV ON D.kendra_id = DV.driver_id
                ) AS match2 ON match1.vehicle_id = match2.vehicle_id AND match1.driver_id != match2.driver_id
                GROUP BY 
                match1.driver_id, 
                match1.driver, 
                match1.street, 
                match1.lat, 
                match1.lng, 
                match1.vehicle_id, 
                match1.manager, 
                match1.shift, 
                match1.center, 
                match1.province, 
                match2.driver_id, 
                match1.exchange_location
                ORDER BY match1.driver_id;
    """)
    
    drivers_df = pd.read_sql(query, engine, params={"province_ids": province_ids})
    
    drivers_df = drivers_df.replace({np.nan: None})
    
    drivers_gdf = gpd.GeoDataFrame(drivers_df, geometry=gpd.points_from_xy(drivers_df.lng, drivers_df.lat), crs='EPSG:4326')
    
    drivers_list_dict = [
        {
            "coordinates": [driver.geometry.x, driver.geometry.y],
            "color": [255, 0, 0, 255],  # Example color: red
            "radius": 50,  # Example radius
            "name": driver["driver"],
            "street": driver["street"],
            "manager": driver["manager"],
            "shift": driver["shift"],
            "center": driver["center"],
            "province": driver["province"],
            "is_matched": driver["is_matched"],
            "matched_driver_id": driver["matched_driver_id"],
            "matched_with": driver["matched_with"],
            "exchange_location": driver["exchange_location"],
        }
        for index, driver in drivers_gdf.iterrows()
    ]
    
    return drivers_gdf, drivers_list_dict