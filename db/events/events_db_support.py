import os
import pandas as pd
from sqlalchemy import text, bindparam
from datetime import datetime, timedelta
from db.db_connect import localauth_dev, localauth_stg, localauth_prod, connect, kndauth
import math

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    database = localauth_stg
elif app_env == 'dev':
    database = localauth_dev
else:
    database = localauth_prod

def fetch_driver_events_by_period_for_managers(start_date, end_date, managers=None):
    engine = connect(kndauth)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    query = """
        SELECT 
            se.id as event_id,
            e.id,
            CONCAT(e.first_name, ' ', e.last_name) AS employee,
            CONCAT(e2.first_name, ' ', e2.last_name) AS manager,
            schedule_event_type.name AS event,
            se.init_date_time AS start,
            se.end_date_time AS end
        FROM 
            schedule_event se
        JOIN employee e ON se.employee_id = e.id
        JOIN employee e2 ON e.fleet_manager_id = e2.id
        JOIN schedule_event_type ON se.type_id = schedule_event_type.id
        WHERE 
            e.status = 'active'
            AND (
                (se.init_date_time BETWEEN :start_date AND :end_date)
                OR (se.end_date_time BETWEEN :start_date AND :end_date)
                OR (se.init_date_time < :start_date AND se.end_date_time > :end_date)
            )
            AND se.deleted_at IS NULL
    """
    
    params = {
        'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
        'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if managers and managers != ['all']:
        query += " AND CONCAT(e2.first_name, ' ', e2.last_name) IN :managers"
        query = text(query).bindparams(bindparam('managers', expanding=True))
        params['managers'] = managers
    else:
        query = text(query)
    
    df = pd.read_sql(query, engine, params=params)
    
    return df

def fetch_driver_events_by_period_for_drivers(start_date, end_date, drivers=None):
    engine = connect(kndauth)
    start_date = pd.to_datetime(start_date)
    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = pd.to_datetime(end_date)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    query = """
        SELECT 
            se.id as event_id,
            e.id,
            CONCAT(e.first_name, ' ', e.last_name) AS employee,
            CONCAT(e2.first_name, ' ', e2.last_name) AS manager,
            schedule_event_type.name AS event,
            se.init_date_time AS start,
            se.end_date_time AS end
        FROM 
            schedule_event se
        JOIN employee e ON se.employee_id = e.id
        JOIN employee e2 ON e.fleet_manager_id = e2.id
        JOIN schedule_event_type ON se.type_id = schedule_event_type.id
        WHERE 
            e.status = 'active'
            AND e.fleet_manager_id IS NOT NULL  -- Exclude managers
            AND (
                (se.init_date_time BETWEEN :start_date AND :end_date)
                OR (se.end_date_time BETWEEN :start_date AND :end_date)
                OR (se.init_date_time < :start_date AND se.end_date_time > :end_date)
            )
            AND se.deleted_at IS NULL
    """
    
    params = {
        'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
        'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if drivers and drivers != ['all']:
        query += " AND e.id IN :drivers"
        query = text(query).bindparams(bindparam('drivers', expanding=True))
        params['drivers'] = drivers
    else:
        query = text(query)
    
    df = pd.read_sql(query, engine, params=params)
    
    return df

def get_min_max_dates_from_schedule_events():
    engine = connect(kndauth)
    query = text("SELECT MIN(init_date_time) AS min_date, MAX(end_date_time) AS max_date FROM schedule_event;")
    df = pd.read_sql(query, engine)
    return df.iloc[0]['min_date'], df.iloc[0]['max_date']

def fetch_managers():
    engine = connect(kndauth)
    query = """
        SELECT DISTINCT
            e2.id,
            CONCAT(e2.first_name, ' ', e2.last_name) AS name
        FROM 
            employee e
        JOIN employee e2 ON e.fleet_manager_id = e2.id
        WHERE 
            e2.status = 'active'
        ORDER BY 
            name
    """
    managers_df = pd.read_sql(text(query), engine)
    return managers_df

def fetch_event_options():
    engine = connect(kndauth)
    query = text("SELECT DISTINCT name FROM schedule_event_type;")
    events_df = pd.read_sql(query, engine)
    return events_df

def fetch_employees_in_schedule_event(start_date, end_date):
    engine = connect(kndauth)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    query = """
        SELECT DISTINCT
            e.id,
            CONCAT(e.first_name, ' ', e.last_name) AS name
        FROM 
            schedule_event se
        JOIN employee e ON se.employee_id = e.id
        LEFT JOIN employee e2 ON e.fleet_manager_id = e2.id
        JOIN employee_shifts es ON se.employee_id = es.employee_id
        WHERE 
            se.deleted_at IS NULL
            AND e.status = 'active'
            AND e.fleet_manager_id IS NOT NULL  -- Exclude managers
            AND es.end_date IS NULL
            AND (
                (se.init_date_time BETWEEN :start_date AND :end_date)
                OR (se.end_date_time BETWEEN :start_date AND :end_date)
                OR (se.init_date_time < :start_date AND se.end_date_time > :end_date)
            )
    """
    
    params = {
        'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
        'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    query = text(query)
    df = pd.read_sql(query, engine, params=params)
    return df