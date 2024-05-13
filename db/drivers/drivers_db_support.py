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


def fetch_drivers_exchange_location_and_shift():
    engine = connect(database)
    query = """
    SELECT 
        d.name AS name,
        e.name AS exchange_location,
        s.name AS shift
    FROM 
        Drivers d
        LEFT JOIN DriversVehiclesExchangeLocations dve ON d.kendra_id = dve.driver_id
        LEFT JOIN ExchangeLocations e ON dve.exchange_location_id = e.id
        LEFT JOIN Shifts s ON d.shift_id = s.id;
    """
    drivers_exchange_location_and_shift_df = pd.read_sql(query, engine)
    return drivers_exchange_location_and_shift_df

