import os
import pandas as pd
from sqlalchemy import text
from db.db_connect import localauth_dev, localauth_stg, localauth_prod, connect

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    database = localauth_stg
elif app_env == 'dev':
    database = localauth_dev
else:
    database = localauth_prod


def fetch_driver_count_per_exchange_location_and_shift():
    engine = connect(database)
    query = """
    SELECT 
        e.name AS exchange_location,
        s.name AS shift,
        COUNT(*) AS count
    FROM 
        DriversVehiclesExchangeLocations dve
        JOIN Drivers d ON dve.driver_id = d.kendra_id
        JOIN ExchangeLocations e ON dve.exchange_location_id = e.id
        JOIN Shifts s ON d.shift_id = s.id
    GROUP BY 
        e.name, s.name;
    """
    driver_count_per_exchange_location_and_shift_df = pd.read_sql(query, engine)
    return driver_count_per_exchange_location_and_shift_df

