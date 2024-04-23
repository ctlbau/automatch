import os
import pandas as pd
from datetime import datetime
from db_connect import localauth_dev, localauth_stg, localauth_prod, companies, connect, kndauth
from sqlalchemy import text
import numpy as np

from dotenv import load_dotenv
thisdir = os.path.dirname(__file__)
envdir = os.path.dirname(thisdir)

load_dotenv(os.path.join(envdir, '.env'))

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    localauth = localauth_stg
elif app_env == 'dev':
    localauth = localauth_dev
else:
    localauth = localauth_prod

def get_vehicle_stati():
    engine = connect(kndauth)
    all_ids = companies['all']
    all_companies = ', '.join(map(str, all_ids))
    vehicle_query = f"""
            SELECT
                vehicle.id AS kendra_id,
                vehicle.license_plate_number AS plate,
                vehicle.status AS status,
                employee.id as manager_id,
                CONCAT(employee.first_name, ' ', employee.last_name) AS manager,
                vehicle.company_id AS company_id,
                company.name AS company,
                center.id AS center_id,
                center.name AS center
            FROM vehicle
                INNER JOIN company ON vehicle.company_id = company.id
                INNER JOIN center ON vehicle.operating_center_id = center.id
                LEFT JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
                LEFT JOIN employee ON vehicle_group.fleet_manager_id = employee.id
            WHERE vehicle.company_id IN ({all_companies})
        """
    vehicle_df = pd.read_sql(vehicle_query, engine)
    manager_query = f"""
            SELECT DISTINCT
                employee.id as manager_id,
                CONCAT(employee.first_name, ' ', employee.last_name) AS manager
            FROM vehicle
                INNER JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
                INNER JOIN employee ON vehicle_group.fleet_manager_id = employee.id
            WHERE vehicle.company_id IN ({all_companies})
        """
    manager_df = pd.read_sql(manager_query, engine)
    return vehicle_df, manager_df

exchange_locations = {
        'parking_lot': 'Campa de Auro',
        'parking_1': 'Parking Marqués de Urquijo',
        'parking_2': 'Parking Reyes Magos',
        'parking_3': 'Campa de Coslada',
        'outside_exchange': 'Cambio fuera',
        'home_full_shift': 'Turno completo en casa'
    }

def synchronize_exchange_locations(exchange_locations=exchange_locations):

    kendra_engine = connect(kndauth)
    local_engine = connect(localauth)
    
    if kendra_engine and local_engine:
        # Retrieve unique exchange location keys from Kendra
        with kendra_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT vehicle.location AS exchange_location
                FROM vehicle
            """))
            # Ensure result rows are accessed as dictionaries
            kendra_location_keys = {row['exchange_location'] for row in result.mappings() if row['exchange_location'] is not None}
        
        with local_engine.begin() as conn:
            # Retrieve current location names from local ExchangeLocations table
            current_locations_result = conn.execute(text("SELECT name FROM ExchangeLocations;"))
            current_locations = {row['name'] for row in current_locations_result.mappings()}

            for key in kendra_location_keys:
                # Map the key to its descriptive name, or use the key itself if not found in the map
                location_name = exchange_locations.get(key, key)
                
                # Skip attempting to insert NULL or empty strings
                if location_name and location_name not in current_locations:
                    conn.execute(text("INSERT INTO ExchangeLocations (name) VALUES (:location_name);"),
                                 {'location_name': location_name})
                    # After inserting, add it to current_locations to avoid trying to insert it again
                    current_locations.add(location_name)




def sync_driver_vehicle_relationships(kndauth, localauth):
    engine_knd = connect(kndauth)
    engine_local = connect(localauth)
    
    # Fetch current state from both databases
    knd_query = text("""
                        SELECT
                            e.id AS driver_id,
                            v.id AS vehicle_id,
                            v.location AS exchange_location
                        FROM
                            vehicle v
                            INNER JOIN vehicle_allocation va ON v.id = va.vehicle_id
                            INNER JOIN employee e ON va.employee_id = e.id
                            AND va.from_date <= current_date()
                            AND (va.to_date >= current_date() OR va.to_date IS NULL)
                            AND va.deleted_at IS NULL
                        WHERE
                            v.status = 'active'
                            AND v.deleted_at IS NULL
                            AND e.status = 'active'
                        ORDER BY
                            e.id, v.id;
                        """)
    local_query = text("SELECT driver_id, vehicle_id, exchange_location_id FROM DriversVehiclesExchangeLocations")
    
    knd_triples = set()
    local_triples = set()
    
    with engine_knd.connect() as conn_knd:
        knd_triples = set(conn_knd.execute(knd_query).fetchall())
    
    with engine_local.connect() as conn_local:
        local_triples = set(conn_local.execute(local_query).fetchall())
    
    # Identify differences
    to_delete = local_triples - knd_triples
    to_insert = knd_triples - local_triples
    
    # Update localauth
    with engine_local.begin() as transaction:
        try:
            # Delete outdated triples
            for triple in to_delete:
                if triple[2] is None:
                    # Handle NULL exchange_location_id explicitly
                    delete_query = text("""
                        DELETE FROM DriversVehiclesExchangeLocations 
                        WHERE driver_id = :driver_id AND vehicle_id = :vehicle_id AND exchange_location_id IS NULL
                    """)
                    transaction.execute(delete_query, {'driver_id': triple[0], 'vehicle_id': triple[1]})
                else:
                    # Handle non-NULL exchange_location_id
                    delete_query = text("""
                        DELETE FROM DriversVehiclesExchangeLocations 
                        WHERE driver_id = :driver_id AND vehicle_id = :vehicle_id AND exchange_location_id = :exchange_location_id
                    """)
                    transaction.execute(delete_query, {'driver_id': triple[0], 'vehicle_id': triple[1], 'exchange_location_id': triple[2]})
            
             # Insert new triples
            for triple in to_insert:
                # Map exchange_location to exchange_location_id
                exchange_location_id = get_or_create_exchange_location(transaction, triple[2])  # Adjust this function call as needed
                insert_query = text("""
                    INSERT INTO DriversVehiclesExchangeLocations (driver_id, vehicle_id, exchange_location_id)
                    SELECT :driver_id, :vehicle_id, :exchange_location_id
                    WHERE EXISTS (
                        SELECT 1 FROM Drivers d WHERE d.kendra_id = :driver_id
                    ) AND EXISTS (
                        SELECT 1 FROM Vehicles v WHERE v.kendra_id = :vehicle_id
                    )
                    ON DUPLICATE KEY UPDATE
                    exchange_location_id = VALUES(exchange_location_id);
                """)
                transaction.execute(insert_query, {
                    'driver_id': triple[0], 
                    'vehicle_id': triple[1],
                    'exchange_location_id': exchange_location_id
                })

            transaction.commit()
            print("DriversVehicles data synchronized successfully.")
        except Exception as e:
            transaction.rollback()
            print(f"An error occurred during synchronization: {e}")
            raise




def get_or_create_exchange_location(conn, location_key):
    # Use the global mapping to resolve location names
    location_name = exchange_locations.get(location_key, location_key)

    if location_name is None:
        return None
    
    normalized_location_name = location_name.strip().lower()
    
    # Attempt to fetch the ID of the existing location
    fetch_id_query = text("""
        SELECT id FROM ExchangeLocations WHERE LOWER(TRIM(name)) = :normalized_location_name;
    """)
    result = conn.execute(fetch_id_query, {'normalized_location_name': normalized_location_name})
    location_id = result.scalar()
    
    # If the location does not exist, insert it and get the ID
    if location_id is None:
        insert_query = text("""
            INSERT INTO ExchangeLocations (name) VALUES (:location_name);
        """)
        conn.execute(insert_query, {'location_name': location_name})  # Insert the descriptive name
        conn.commit()
        # Refetch the ID after insertion
        result = conn.execute(fetch_id_query, {'normalized_location_name': normalized_location_name})
        location_id = result.scalar()
    
    return location_id


def ensure_managers_exist(manager_df):
    engine = connect(localauth)
    with engine.connect() as con:
        for _, row in manager_df.iterrows():
            check_query = text("SELECT COUNT(*) FROM Managers WHERE id = :manager_id")
            insert_query = text("INSERT INTO Managers (id, name) VALUES (:manager_id, :manager)")
            result = con.execute(check_query, {'manager_id': row['manager_id']})
            if result.fetchone()[0] == 0:
                con.execute(insert_query, {'manager_id': row['manager_id'], 'manager': row['manager']})

def ensure_companies_exist(df):
    engine = connect(localauth)
    with engine.connect() as con:
        unique_companies = df[['company_id', 'company']].drop_duplicates()
        for _, row in unique_companies.iterrows():
            check_query = text("SELECT COUNT(*) FROM Companies WHERE id = :company_id")
            insert_query = text("INSERT INTO Companies (id, name) VALUES (:company_id, :company)")
            result = con.execute(check_query, {'company_id': row['company_id']})
            if result.fetchone()[0] == 0:
                con.execute(insert_query, {'company_id': row['company_id'], 'company': row['company']})

def ensure_centers_exist(df):
    engine = connect(localauth)
    with engine.connect() as con:
        unique_centers = df[['center_id', 'center']].drop_duplicates()
        for _, row in unique_centers.iterrows():
            check_query = text("SELECT COUNT(*) FROM Centers WHERE id = :center_id")
            insert_query = text("INSERT INTO Centers (id, name) VALUES (:center_id, :center)")
            result = con.execute(check_query, {'center_id': row['center_id']})
            if result.fetchone()[0] == 0:
                con.execute(insert_query, {'center_id': row['center_id'], 'center': row['center']})

def delete_absent_managers():
    engine_knd = connect(kndauth)
    with engine_knd.connect() as con_knd:
        result_knd = con_knd.execute(text("""SELECT
                                            e2.id as id
                                        FROM
                                            employee e
                                        INNER JOIN 
                                            employee e2 ON e2.id = e.fleet_manager_id
                                        WHERE
                                            e.geolocation_latitude IS NOT NULL
                                            AND e.geolocation_longitude IS NOT NULL
                                            AND e.status = 'active'
                                            AND e.position_id in (6, 30)
                                        GROUP BY
                                            e2.id
                                        ORDER BY
                                            e2.id;"""))
        knd_manager_ids = set([row[0] for row in result_knd.fetchall()])

    engine_local = connect(localauth)
    with engine_local.connect() as con_local:
        result_local = con_local.execute(text("SELECT id FROM Managers"))
        local_manager_ids = set([row[0] for row in result_local.fetchall()])

        managers_to_delete = local_manager_ids - knd_manager_ids
        purged_managers_count = 0

        for manager_id in managers_to_delete:
            # Check for dependencies in the Vehicles table
            vehicles_count = con_local.execute(text("SELECT COUNT(*) FROM Vehicles WHERE manager_id = :manager_id"), {'manager_id': manager_id}).fetchone()[0]

            # Check for dependencies in the Drivers table
            drivers_count = con_local.execute(text("SELECT COUNT(*) FROM Drivers WHERE manager_id = :manager_id"), {'manager_id': manager_id}).fetchone()[0]

            if vehicles_count == 0 and drivers_count == 0:
                # If no dependencies are found in either table, it's safe to delete the manager
                con_local.execute(text("DELETE FROM Managers WHERE id = :manager_id", {'manager_id': manager_id}))
                purged_managers_count += 1
            else:
                # Dependencies exist, so we skip deleting this manager
                print(f"Skipping deletion of manager {manager_id} due to existing dependencies in Vehicles or Drivers tables.")

        print(f"Completed checking and deleting absent managers from local database. Total managers purged: {purged_managers_count}.")

def insert_vehicle_data(df, engine=connect(localauth)):
    df['date'] = pd.to_datetime(datetime.now().date())

    # Convert NaN values to None for the entire DataFrame
    df = df.replace({np.nan: None})

    with engine.connect() as con:
        for _, row in df.iterrows():
            query = text("""
            INSERT INTO Vehicles (kendra_id, plate, status, date, company_id, center_id, manager_id)
                VALUES (:kendra_id, :plate, :status, :date, :company_id, :center_id, :manager_id)
                ON DUPLICATE KEY UPDATE
                plate = VALUES(plate),
                status = VALUES(status),
                date = VALUES(date),
                company_id = VALUES(company_id),
                center_id = VALUES(center_id),
                manager_id = VALUES(manager_id);
            """)
            params = row.to_dict()
            
            # Ensure date is in the correct format (date only) before executing
            params['date'] = params['date'].date() if isinstance(params['date'], pd.Timestamp) else params['date']

            try:
                con.execute(query, params)
            except Exception as e:
                print(f"Error executing query: {e}")

        con.commit()
        print(f"Successful insertion of {len(df)} rows into Vehicles table.")

def fetch_and_insert_shift_data(kndauth, localauth):
    select_query = text("""SELECT s.id AS shift_id, s.name AS name FROM shift s ORDER BY s.id;""")
    insert_query = text("""INSERT IGNORE INTO Shifts (id, name) VALUES (:id, :name);""")

    engine_knd = connect(kndauth)
    with engine_knd.connect() as knd_conn:
        result = knd_conn.execute(select_query)
        shifts = result.fetchall()
    
    engine_local = connect(localauth)
    with engine_local.connect() as local_conn:
        for shift in shifts:
            local_conn.execute(insert_query, {'id': shift[0], 'name': shift[1]})
        local_conn.commit()
        print("Shifts data inserted successfully")

def fetch_and_insert_provinces(kndauth, localauth):
    select_query = text("""SELECT p.id, p.name FROM province p ORDER BY p.id;""")
    # Correct the placeholders to use named parameters
    insert_query = text("""INSERT IGNORE INTO Provinces (id, name) VALUES (:id, :name);""")

    engine_knd = connect(kndauth)
    with engine_knd.connect() as knd_conn:
        result = knd_conn.execute(select_query)
        provinces = result.fetchall()
    
    engine_local = connect(localauth)
    with engine_local.connect() as local_conn:
        for province in provinces:
            # Pass parameters as a dictionary matching the named placeholders
            local_conn.execute(insert_query, {'id': province[0], 'name': province[1]})
        local_conn.commit()
        print("Provinces data inserted successfully")

def delete_absent_drivers():
    # Connect to the kndauth database and fetch all active driver IDs
    engine_knd = connect(kndauth)
    knd_driver_ids_query = """
    SELECT
        e.id
    FROM
        employee e
        INNER JOIN employee e2 ON e2.id = e.fleet_manager_id
        INNER JOIN employee_contract c ON e.current_contract_id = c.id
        INNER JOIN center ce ON c.working_center_id = ce.id
        INNER JOIN address a ON ce.address_id = a.id
        INNER JOIN employee_shifts es ON e.id = es.employee_id
        INNER JOIN shift s ON s.id = es.shift_id
    WHERE
        e.geolocation_latitude IS NOT NULL
        AND e.geolocation_longitude IS NOT NULL
        AND e.status = 'active'
        AND (es.end_date IS NULL OR es.end_date >= date(now()))
        AND es.start_date <= date(now())
        AND e.position_id in (6, 30)
        AND es.deleted_at IS NULL
    """
    with engine_knd.connect() as conn_knd:
        result_knd = conn_knd.execute(text(knd_driver_ids_query))
        knd_driver_ids = set([row[0] for row in result_knd.fetchall()])

    # Connect to localauth and fetch all driver IDs
    engine_local = connect(localauth)
    local_driver_ids_query = "SELECT kendra_id FROM Drivers"
    with engine_local.connect() as conn_local:
        result_local = conn_local.execute(text(local_driver_ids_query))
        local_driver_ids = set([row[0] for row in result_local.fetchall()])

    # Identify drivers in database not in kndauth
    absent_driver_ids = local_driver_ids - knd_driver_ids
    deleted_drivers_count = 0

    # Delete absent drivers from the database database
    delete_driver_query = "DELETE FROM Drivers WHERE kendra_id = :kendra_id"
    with engine_local.connect() as conn_local:
        transaction = conn_local.begin()  # Start a new transaction
        try:
            for driver_id in absent_driver_ids:
                conn_local.execute(text(delete_driver_query), {'kendra_id': driver_id})
                deleted_drivers_count += 1
            transaction.commit()  # Commit the transaction if no errors occurred
        except Exception as e:
            transaction.rollback()  # Roll back the transaction in case of error
            print(f"An error occurred: {e}")  # Log or print the error
            raise  # Re-raise the exception to handle it or log it as needed

    print(f"Deleted {deleted_drivers_count} absent drivers from the local database.")

def fetch_and_insert_drivers(kndauth, localauth, manager_df):
    manager_ids = manager_df['manager_id'].tolist()
    placeholders = ','.join([':manager_id_' + str(i) for i in range(len(manager_ids))])
    parameters = {'manager_id_' + str(i): manager_id for i, manager_id in enumerate(manager_ids)}
    query_string = f"""
    SELECT
        e.id as kendra_id,
        CONCAT(e.first_name, ' ', e.last_name) AS name,
        e.address_street AS street,
        e.address_city AS city,
        e.address_country AS country,
        e.address_zip_code AS zip_code,
        e.geolocation_latitude AS lat,
        e.geolocation_longitude AS lng,
        a.province_id AS province_id,
        e.fleet_manager_id AS manager_id,
        s.id as shift_id
    FROM
        employee e
        INNER JOIN employee e2 ON e2.id = e.fleet_manager_id
        INNER JOIN employee_contract c ON e.current_contract_id = c.id
        INNER JOIN center ce ON c.working_center_id = ce.id
        INNER JOIN address a ON ce.address_id = a.id
        INNER JOIN employee_shifts es ON e.id = es.employee_id
        INNER JOIN shift s ON s.id = es.shift_id
        
    WHERE
        # e.geolocation_latitude IS NOT NULL
        # AND e.geolocation_longitude IS NOT NULL
        e.status = 'active'
        AND (es.end_date IS NULL OR es.end_date >= date(now()))
        AND es.start_date <= date(now())
        AND e.position_id in (6, 30)
        AND es.deleted_at IS NULL
        AND a.province_id in (28, 8, 29, 41, 46)
        AND e.fleet_manager_id IN ({placeholders})
    ORDER BY
        e.id;"""
    select_query = text(query_string)
    
    insert_query = text("""INSERT INTO Drivers (kendra_id, name, street, city, country, zip_code, lat, lng, province_id, manager_id, shift_id) 
    VALUES (:kendra_id, :name, :street, :city, :country, :zip_code, :lat, :lng, :province_id, :manager_id, :shift_id) 
    ON DUPLICATE KEY UPDATE 
    name = VALUES(name), street = VALUES(street), city = VALUES(city), country = VALUES(country), zip_code = VALUES(zip_code), 
    lat = VALUES(lat), lng = VALUES(lng), province_id = VALUES(province_id), manager_id = VALUES(manager_id), shift_id = VALUES(shift_id);""")

    engine_knd = connect(kndauth)
    with engine_knd.connect() as knd_conn:
        result = knd_conn.execute(select_query, parameters)
        drivers = result.fetchall()
    
    engine_local = connect(localauth)
    with engine_local.connect() as local_conn:
        for driver in drivers:
            local_conn.execute(insert_query, {
                'kendra_id': driver.kendra_id, 
                'name': driver.name, 
                'street': driver.street, 
                'city': driver.city, 
                'country': driver.country, 
                'zip_code': driver.zip_code, 
                'lat': driver.lat, 
                'lng': driver.lng, 
                'province_id': driver.province_id, 
                'manager_id': driver.manager_id, 
                'shift_id': driver.shift_id
            })
        local_conn.commit()
        print("Drivers data inserted successfully")


if __name__ == "__main__":
    df, manager_df = get_vehicle_stati()
    ensure_managers_exist(manager_df)
    delete_absent_managers()
    ensure_companies_exist(df)
    ensure_centers_exist(df)
    insert_vehicle_data(df)
    delete_absent_drivers()
    fetch_and_insert_shift_data(kndauth, localauth)
    fetch_and_insert_provinces(kndauth, localauth)
    fetch_and_insert_drivers(kndauth, localauth, manager_df)
    synchronize_exchange_locations()
    sync_driver_vehicle_relationships(kndauth, localauth)
    fetch_and_insert_drivers(kndauth, localauth, manager_df)
