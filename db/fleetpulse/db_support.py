import os
import pymysql
import logging
import pandas as pd
import time
from datetime import date
from sqlalchemy import text
from db.db_connect import connect, localauth, companies

def fetch_managers():
    engine = connect(localauth)
    query = text("SELECT id, name FROM Managers;")
    managers_df = pd.read_sql(query, engine)
    return managers_df

def fetch_statuses():
    engine = connect(localauth)
    query = text("SELECT DISTINCT status FROM Vehicles;")
    statuses_df = pd.read_sql(query, engine)
    return statuses_df  # Return the DataFrame directly, without calling it

def fetch_date_range():
    engine = connect(localauth)
    query = text("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM Vehicles;")
    with engine.connect() as connection:
        result = connection.execute(query).fetchone()
    min_date, max_date = result
    return min_date, max_date

def fetch_plates():
    engine = connect(localauth)
    query = text("SELECT DISTINCT plate FROM Vehicles;")
    plates_df = pd.read_sql(query, engine)
    return plates_df

def fetch_vehicles(company=companies["all"], from_date=None, to_date=None):
    engine = connect(localauth)
    company_ids = ', '.join(map(str, companies[company]))

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
        {date_condition};
    """
    df = pd.read_sql(text(query), engine)
    return df

def select_plate(plate, from_date=None, to_date=None):
    engine = connect(localauth)
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
    engine = connect(localauth)
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