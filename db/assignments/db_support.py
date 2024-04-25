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

def fetch_vehicle_shifts(exchange_locations=None, gestores=None):
    engine = connect(database)
    columns = ["plate", "Mañana", "Tarde", "TP-V-D", "TP-L-V", "L-J", "L-J_(40h)", "Turno_Completo", "number_of_drivers", "manager", "center", "exchange_location", "driver_ids"]
    
    if gestores is None:
        gestores = ["Alejandro Garcia Coscolla", "Alfonso Pradas Mateos", "Carlos Sanchez-Fuentes Garcia", "Daniel Gonzalo Garcia", "Deogracias Sanchez  Muñoz", "Emilio Barberan Casanova", "Fernando Mario Fernández Pérez", "Francisco Gómez Martín", "Gonzalo Torralba Rodriguez", "Irene Hinojal Berbis", "Javier Mendez Moreno", "Jesus Pablo Diaz Blazquez", "Jose Antonio Lage Barrantes", "Olga Rosas Roman", "Pedro Arribas Dorado"]
        gestores = ', '.join(f"'{g}'" for g in gestores)
        gestores_condition = f"AND m.name IN ({gestores})"
    else:
        gestores_condition = ""
    
    if exchange_locations:
        exchange_locations = ', '.join(f"'{el}'" for el in exchange_locations)
        exchange_locations_condition = f"AND el.name IN ({exchange_locations})"
    else:
        exchange_locations_condition = ""
    
    query = f"""
        SELECT 
            v.plate,
            MAX(CASE WHEN s.name = 'Mañana' THEN 1 ELSE 0 END) AS 'Mañana',
            MAX(CASE WHEN s.name = 'Tarde' THEN 1 ELSE 0 END) AS 'Tarde',
            MAX(CASE WHEN s.name = 'Turno Completo' THEN 1 ELSE 0 END) AS 'Turno_Completo',
            MAX(CASE WHEN s.name = 'J&T Turno diario' THEN 1 ELSE 0 END) AS 'J&T_Turno_diario',
            MAX(CASE WHEN s.name = 'J&T Turno fines de semana' THEN 1 ELSE 0 END) AS 'J&T_Turno_fines_de_semana',
            MAX(CASE WHEN s.name = 'TP-V-D' THEN 1 ELSE 0 END) AS 'TP-V-D',
            MAX(CASE WHEN s.name = 'TP-L-V' THEN 1 ELSE 0 END) AS 'TP-L-V',
            MAX(CASE WHEN s.name = 'JT-Turno Doble V,D' THEN 1 ELSE 0 END) AS 'JT-Turno_Doble_V,D',
            MAX(CASE WHEN s.name = 'JT-Turno Doble Nocturno' THEN 1 ELSE 0 END) AS 'JT-Turno Doble Nocturno',
            MAX(CASE WHEN s.name = 'L-J' THEN 1 ELSE 0 END) AS 'L-J',
            MAX(CASE WHEN s.name = 'L-J (40h)' THEN 1 ELSE 0 END) AS 'L-J_(40h)',
            COUNT(DISTINCT dvel.driver_id) AS number_of_drivers,
            # GROUP_CONCAT(DISTINCT dvel.driver_id ORDER BY dvel.driver_id SEPARATOR ', ') AS driver_ids,
            m.name AS manager,
            c.name AS center,
            el.name AS exchange_location
        FROM 
            Vehicles v
        LEFT JOIN 
            DriversVehiclesExchangeLocations dvel ON v.kendra_id = dvel.vehicle_id
        LEFT JOIN 
            Drivers d ON dvel.driver_id = d.kendra_id
        LEFT JOIN 
            Shifts s ON d.shift_id = s.id
        LEFT JOIN
            Managers m ON v.manager_id = m.id
        LEFT JOIN
            Centers c ON v.center_id = c.id
        LEFT JOIN
            ExchangeLocations el ON dvel.exchange_location_id = el.id
        WHERE 
            v.date = CURDATE() AND 
            v.status IN ('available', 'active')
            {exchange_locations_condition}
            {gestores_condition}
        GROUP BY 
            v.plate, m.name, c.name, el.name;
    """
    
    vehicle_shifts_df = pd.read_sql(text(query), engine)
    vehicle_shifts_df = vehicle_shifts_df.drop(columns=[col for col in vehicle_shifts_df.columns if col not in columns])
    
    return vehicle_shifts_df