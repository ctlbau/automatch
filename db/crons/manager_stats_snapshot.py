import os
import pandas as pd
import numpy as np
from ..db_connect import localauth_dev, localauth_stg, localauth_prod, connect

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db.automatch.db_support import fetch_drivers
from utils.geo_utils import calculate_driver_distances_and_paths
from utils.agg_utils import get_manager_distance_stats

from datetime import datetime
from dotenv import load_dotenv

import warnings
warnings.filterwarnings("ignore", message="Mean of empty slice")

thisdir = os.path.dirname(__file__)
parentdir = os.path.dirname(thisdir)
envdir = os.path.dirname(parentdir)

load_dotenv(os.path.join(envdir, '.env'))

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    localauth = localauth_stg
elif app_env == 'dev':
    localauth = localauth_dev
else:
    localauth = localauth_prod


def fetch_prepare_and_insert_manager_stats_snapshot():
    engine = connect(localauth)
    today = datetime.today().date()
    
    drivers_gdf, _ = fetch_drivers([28, 46, 8, 41, 29])  
    drivers_gdf_w_paths_and_distances, error_df = calculate_driver_distances_and_paths(drivers_gdf)
    manager_stats_general = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, "All")
    manager_stats_general['exchange_location'] = 'General'
    manager_stats_general['date'] = today
    manager_stats_cambio = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, "Cambio fuera")
    manager_stats_cambio['exchange_location'] = 'Cambio fuera'
    manager_stats_cambio['date'] = today
    manager_stats_marques = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, "Parking Marqués de Urquijo")
    manager_stats_marques['exchange_location'] = 'Parking Marqués de Urquijo'
    manager_stats_marques['date'] = today
    manager_stats_reyes = get_manager_distance_stats(drivers_gdf_w_paths_and_distances, "Parking Reyes Magos")
    manager_stats_reyes['exchange_location'] = 'Parking Reyes Magos'
    manager_stats_reyes['date'] = today

    manager_stats = pd.concat([manager_stats_general, manager_stats_cambio, manager_stats_marques, manager_stats_reyes], axis=0)
    manager_stats = manager_stats.replace({np.nan: None})


    sql = text("""
    INSERT INTO ManagerStatsHistorical
        (date, manager, total_drivers, matched_drivers, unmatched_drivers, matched_percentage, avg_distance, median_distance, min_distance, max_distance, exchange_location)
    VALUES
        (:date, :manager, :total_drivers, :matched_drivers, :unmatched_drivers, :matched_percentage, :avg_distance, :median_distance, :min_distance, :max_distance, :exchange_location)
    ON DUPLICATE KEY UPDATE
        date = VALUES(date),
        manager = VALUES(manager),
        total_drivers = VALUES(total_drivers),
        matched_drivers = VALUES(matched_drivers),
        unmatched_drivers = VALUES(unmatched_drivers),
        matched_percentage = VALUES(matched_percentage),
        avg_distance = VALUES(avg_distance),
        median_distance = VALUES(median_distance),
        min_distance = VALUES(min_distance),
        max_distance = VALUES(max_distance),
        exchange_location = VALUES(exchange_location);       
    """)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(sql, manager_stats.to_dict(orient='records'))
                transaction.commit()
                print(f"Inserted {len(manager_stats)} rows into ManagerStatsHistorical table")
            except Exception as e:
                transaction.rollback()
                print("Transaction failed and was rolled back.")
                print(e)
    except SQLAlchemyError as e:
        print("Failed to connect or execute transaction.")
        print(e)

if __name__ == "__main__":
    fetch_prepare_and_insert_manager_stats_snapshot()

