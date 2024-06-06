import os
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
from db.db_connect import localauth_dev, localauth_stg, localauth_prod, kndauth, connect

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

def fetch_driver_events_by_week_of_year(year, week, manager=None):
    engine = connect(kndauth)
    monday, sunday = get_week_start_end(year, week)
    
    query = """
        SELECT 
            se.id as event_id,
            e.id,
            CONCAT(e.first_name, ' ', e.last_name) AS employee,
            CONCAT(e2.first_name, ' ', e2.last_name) AS manager,
            v.license_plate_number AS plate,
            shift.name AS shift,
            schedule_event_type.name AS event
        FROM 
            schedule_event se
        JOIN employee e ON se.employee_id = e.id
        JOIN employee e2 ON e.fleet_manager_id = e2.id
        JOIN employee_shifts es ON se.employee_id = es.employee_id
        JOIN shift ON shift.id = es.shift_id
        JOIN schedule_event_type ON se.type_id = schedule_event_type.id
        LEFT JOIN vehicle_allocation va ON se.employee_id = va.employee_id
            AND (
                (va.from_date BETWEEN :monday AND :sunday)
                OR (COALESCE(va.to_date, va.deleted_at) BETWEEN :monday AND :sunday)
                OR (va.from_date <= :monday AND COALESCE(va.to_date, va.deleted_at) >= :sunday)
                OR (va.to_date IS NULL AND va.deleted_at IS NULL)
            )
        LEFT JOIN vehicle v ON va.vehicle_id = v.id
        WHERE 
            e.status = 'active'
            AND (
                (se.init_date_time BETWEEN :monday AND :sunday)
                OR (se.end_date_time BETWEEN :monday AND :sunday)
                OR (se.init_date_time < :monday AND se.end_date_time > :sunday)
            )
            AND se.deleted_at IS NULL
            AND es.end_date IS NULL
    """
    
    if manager and manager.lower() != 'all':
        query += " AND CONCAT(e2.first_name, ' ', e2.last_name) = :manager"
    
    query = text(query)
    
    params = {
        'monday': monday.strftime('%Y-%m-%d'),
        'sunday': sunday.strftime('%Y-%m-%d')
    }
    
    if manager and manager.lower() != 'all':
        params['manager'] = manager
    
    df = pd.read_sql(query, engine, params=params)
    df['week'] = week
    df['year'] = year
    df['monday'] = monday
    df['sunday'] = sunday
    
    return df

def get_week_start_end(year, week):
    first_day_of_year = datetime(year, 1, 1)
    first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday() if first_day_of_year.weekday() != 0 else 0))
    monday = first_monday + timedelta(weeks=week - 1)
    
    if monday.year > year:
        monday = datetime(year, 12, 31) - timedelta(days=datetime(year, 12, 31).weekday())
    sunday = monday + timedelta(days=6)
    # Set sunday to the end of the day
    sunday = sunday.replace(hour=23, minute=59, second=59)
    
    return monday, sunday

def fetch_driver_events_for_weeks(start_year, start_week, end_year, end_week, manager=None):
    all_weeks_df = []
    
    current_year = start_year
    current_week = start_week
    
    while current_year < end_year or (current_year == end_year and current_week <= end_week):
        df = fetch_driver_events_by_week_of_year(current_year, current_week, manager)
        all_weeks_df.append(df)
        
        if current_week == 52:
            current_week = 1
            current_year += 1
        else:
            current_week += 1
    
    combined_df = pd.concat(all_weeks_df, ignore_index=True)
    combined_df = combined_df.sort_values(by=['year', 'week'])

    defined_plate_df = combined_df[combined_df['plate'].notna()]
    undefined_plate_df = combined_df[combined_df['plate'].isna()]

    employee_ids = undefined_plate_df['id'].unique()

    for employee_id in employee_ids:
        employee_records = defined_plate_df[defined_plate_df['id'] == employee_id]
        
        if not employee_records.empty:
            max_year = employee_records['year'].max()
            max_week = employee_records[employee_records['year'] == max_year]['week'].max()
            last_assigned_row = employee_records[(employee_records['year'] == max_year) & (employee_records['week'] == max_week)]
            last_assigned_plate = last_assigned_row['plate'].values[0]
        else:
            last_assigned_plate = 'unknown'
        
        combined_df.loc[(combined_df['id'] == employee_id) & (combined_df['plate'].isna()), 'plate'] = last_assigned_plate

    return combined_df

def get_min_max_dates_from_schedule_events():
    engine = connect(kndauth)
    query = text("SELECT MIN(init_date_time) AS min_date, MAX(end_date_time) AS max_date FROM schedule_event;")
    df = pd.read_sql(query, engine)
    return df.iloc[0]['min_date'], df.iloc[0]['max_date']

def fetch_managers():
    engine = connect(database)
    query = text("SELECT id, name FROM Managers;")
    managers_df = pd.read_sql(query, engine)
    managers_df = managers_df.sort_values(by='name')
    return managers_df

def fetch_plates():
    engine = connect(kndauth)
    query = text("SELECT license_plate_number AS plate FROM vehicle;")
    plates_df = pd.read_sql(query, engine)
    return plates_df

