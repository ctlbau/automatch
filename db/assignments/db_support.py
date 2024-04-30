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


def fetch_date_range():
    engine = connect(database)
    query = text("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM VehicleShiftsHistorical;")
    with engine.connect() as connection:
        result = connection.execute(query).fetchone()
    min_date, max_date = result
    return min_date, max_date

def fetch_exchange_locations():
    exchange_locations = ['Cambio fuera', 'Parking Reyes Magos', 'Parking Marqués de Urquijo']
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


def fetch_vehicle_shifts(from_date=None, to_date=None):
    engine = connect(database)

    date_condition = ""
    if from_date and to_date:
        date_condition = f"WHERE VSH.date BETWEEN :from_date AND :to_date"
    elif from_date:
        date_condition = f"WHERE VSH.date >= :from_date"
    elif to_date:
        date_condition = f"WHERE VSH.date <= :to_date"

    query = f"""
    SELECT
        VSH.plate, VSH.date, VSH.manager, VSH.center, VSH.number_of_drivers, VSH.manana, VSH.tarde,  VSH.tp_v_d, VSH.tp_l_v, VSH.l_j, VSH.l_j_40h, VSH.turno_completo
    FROM
        VehicleShiftsHistorical VSH
        {date_condition};
    """

    params = {
        'from_date': from_date,
        'to_date': to_date
    }

    df = pd.read_sql(text(query), engine, params=params)
    return df


def create_vehicle_shifts(exchange_locations=None, gestores=None):
    engine = connect(database)
    columns = ["plate", "date", "manana", "tarde", "tp_v_d", "tp_l_v", "l_j", "l_j_40h", "turno_completo", "number_of_drivers", "manager", "center", "exchange_location", "driver_ids"]
    
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
            CURDATE() AS date,
            MAX(CASE WHEN s.name = 'Mañana' THEN 1 ELSE 0 END) AS 'manana',
            MAX(CASE WHEN s.name = 'Tarde' THEN 1 ELSE 0 END) AS 'tarde',
            MAX(CASE WHEN s.name = 'Turno Completo' THEN 1 ELSE 0 END) AS 'turno_completo',
            MAX(CASE WHEN s.name = 'J&T Turno diario' THEN 1 ELSE 0 END) AS 'j&t_Turno_diario',
            MAX(CASE WHEN s.name = 'J&T Turno fines de semana' THEN 1 ELSE 0 END) AS 'j&t_turno_fines_de_semana',
            MAX(CASE WHEN s.name = 'TP-V-D' THEN 1 ELSE 0 END) AS 'tp_v_d',
            MAX(CASE WHEN s.name = 'TP-L-V' THEN 1 ELSE 0 END) AS 'tp_l_v',
            MAX(CASE WHEN s.name = 'JT-Turno Doble V,D' THEN 1 ELSE 0 END) AS 'jt_turno_doble_v,d',
            MAX(CASE WHEN s.name = 'JT-Turno Doble Nocturno' THEN 1 ELSE 0 END) AS 'jt_turno_doble_nocturno',
            MAX(CASE WHEN s.name = 'L-J' THEN 1 ELSE 0 END) AS 'l_j',
            MAX(CASE WHEN s.name = 'L-J (40h)' THEN 1 ELSE 0 END) AS 'l_j_40h',
            COUNT(DISTINCT dvel.driver_id) AS number_of_drivers,
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
