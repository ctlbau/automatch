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

def fetch_provinces():
    engine = connect(database)
    query = text("SELECT id, name FROM Provinces;")
    provinces_df = pd.read_sql(query, engine)
    provinves = ['Madrid', 'Barcelona', 'Valencia', 'Málaga', 'Toledo']
    provinces_df = provinces_df[provinces_df['name'].isin(provinves)]
    provinces_df = provinces_df.sort_values(by='name')
    return provinces_df

def fetch_drivers_exchange_location_and_shift(province_ids: list = None):
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
        LEFT JOIN Shifts s ON d.shift_id = s.id
    """

    if province_ids:
        province_ids_str = ','.join(map(str, province_ids))
        query += f"WHERE province_id IN ({province_ids_str})"
        df = pd.read_sql(query, engine)
    else:
        df = pd.read_sql(query, engine)
        
    return df
