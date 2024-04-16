import os
import pandas as pd
import time
from datetime import date
from sqlalchemy import text

from db.db_connect import localauth_dev, localauth_stg, localauth_prod, companies, connect

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    database = localauth_stg
elif app_env == 'dev':
    database = localauth_dev
else:
    database = localauth_prod


def fetch_managers():
    engine = connect(database)
    query = text("SELECT id, name FROM Managers;")
    managers_df = pd.read_sql(query, engine)
    managers_df = managers_df.sort_values(by='name')
    return managers_df

def fetch_centers():
    centers = ['Clematis Bach Transportation Services S.L.', 
               'Autos Lavapiés S.L. (Madrid)', 
               'Proinvertia Madrid S.L. (Madrid)',
                'Vtc Transfer Sociality S.L.',
                'Afm Portal de Transporte S.L. (Madrid)',
                'Gest VTC Service S.L.',
                'Zater Transportation Services 1525 S.L.',
                'GTX Madrid',
                'Next Band S.L. (Madrid)',
                'Auro Madrid',
                'Do The Right Thing Cars S.L. (Madrid)',
                'Iceberg Smart Cab S.L.',
                'Autos Agrimony Bach Transportation S.L.',
                'Autos Miraz la Bella S.L.',
                'Freetown Business S.L.',
                'Autos Ararat Transportation S.L (Madrid)',
                'Autos Puerta del Sol S.L. (Madrid)',
                'Vtc Kico Cars S.L.',
                'Vtc Felp Transfer S.L.',
                'Inertia Mobility S.L. (Madrid)',
                'Intercambiadores Europeos SL',
                'Mindworld Project S.L',
                'Swift Transports Crt S.L',
                'AUTOS NOROESTE ALQUILER DE COCHES SIN CONDUCTOR SL',
                'Shuttle Vip Madrid',
                'Autos La Maruca Da Serpe S.L. (Madrid)',
                'Libreocupado S.L. (Madrid)',
                'Libreocupado S.L (Málaga)',
                'Alquiler de vehículos con conductor Jaén y Málaga S.L. (MLAGA)',
                'Cibeles Comfort Cars S.L. (Madrid)',
                'Automóviles Zirconio S.L. (Valencia)',
                'Automóviles Titanio S.L. (Valencia)',
                'Libreocupado S.L. (Valencia)',
                'Freetown Business S.L. (Barcelona)',
                'Automóviles Titanio S.L. (Barcelona)',
                'Radio Taxi Barcelona S.L. (Barcelona)',
                'Automóviles Zirconio S.L. (Málaga)',
                'Automóviles Zirconio S.L. (Sevilla)',
                'AYG PRODSERVICES SL',
                'Libreocupado S.L (Barcelona)',]
    engine = connect(database)
    query = text("SELECT id, name FROM Centers;")
    centers_df = pd.read_sql(query, engine)
    centers_df = centers_df[centers_df['name'].isin(centers)]
    centers_df = centers_df.sort_values(by='name')
    return centers_df

def fetch_statuses():
    engine = connect(database)
    query = text("SELECT DISTINCT status FROM Vehicles;")
    statuses_df = pd.read_sql(query, engine)
    return statuses_df

def fetch_date_range():
    engine = connect(database)
    query = text("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM Vehicles;")
    with engine.connect() as connection:
        result = connection.execute(query).fetchone()
    min_date, max_date = result
    return min_date, max_date

def fetch_plates():
    engine = connect(database)
    query = text("SELECT DISTINCT plate FROM Vehicles;")
    plates_df = pd.read_sql(query, engine)
    return plates_df

def fetch_vehicles(centers, company=companies["all"], from_date=None, to_date=None):
    engine = connect(database)
    company_ids = ', '.join(map(str, companies[company]))

    if centers:
        center_ids = ', '.join(map(str, centers))
        center_condition = f"AND V.center_id IN ({center_ids})"
    else:
        center_condition = ""

    date_condition = ""
    if from_date and to_date:
        date_condition = f"AND V.date BETWEEN '{from_date}' AND '{to_date}'"
    elif from_date:
        date_condition = f"AND V.date >= '{from_date}'"
    elif to_date:
        date_condition = f"AND V.date <= '{to_date}'"

    query = f"""
    SELECT
        V.kendra_id, V.date, V.plate, V.status, M.name AS manager, C.name AS company, CTR.name AS center
    FROM
        Vehicles V
        INNER JOIN Companies C ON V.company_id = C.id
        LEFT JOIN Managers M ON V.manager_id = M.id
        LEFT JOIN Centers CTR ON V.center_id = CTR.id
    WHERE
        V.company_id IN ({company_ids})
        {center_condition}
        {date_condition};
    """
    df = pd.read_sql(text(query), engine)
    return df

def select_plate(plate, from_date=None, to_date=None):
    engine = connect(database)
    date_condition = ""
    if from_date and to_date:
        date_condition = f"AND date BETWEEN :from_date AND :to_date"
    elif from_date:
        date_condition = f"AND date >= :from_date"
    elif to_date:
        date_condition = f"AND date <= :to_date"

    query = f"""
    SELECT
        date, status
    FROM
        Vehicles
    WHERE
        plate = :plate
        {date_condition};
    """
    params = {'plate': plate, 'from_date': from_date, 'to_date': to_date}
    df = pd.read_sql(text(query), engine, params=params)
    return df

def get_vehicle_stati():
    engine = connect(database)
    all_ids = companies['all']
    all_companies = ', '.join(map(str, all_ids))

    query = text(f"""
        SELECT
            vehicle.id AS kendra_id,
            vehicle.license_plate_number AS plate,
            vehicle.status,
            employee.id AS manager_id,
            CONCAT(employee.first_name, ' ', employee.last_name) AS manager,
            vehicle.company_id,
            company.name AS company,
            center.id AS center_id,
            center.name AS center
        FROM vehicle
            INNER JOIN company ON vehicle.company_id = company.id
            INNER JOIN center ON vehicle.operating_center_id = center.id
            LEFT JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
            LEFT JOIN employee ON vehicle_group.fleet_manager_id = employee.id
        WHERE vehicle.company_id IN ({all_companies})
    """)

    df = pd.read_sql(query, engine)
    return df