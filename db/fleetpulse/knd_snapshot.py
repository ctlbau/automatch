import os
import pandas as pd
from datetime import datetime
from db.db_connect import *

def get_vehicle_stati():
    with connect(kndauth) as con, con.cursor() as cursor:
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
        vehicle_df = pd.read_sql(vehicle_query, con)
        manager_query = f"""
                SELECT DISTINCT
                    employee.id as manager_id,
                    CONCAT(employee.first_name, ' ', employee.last_name) AS manager
                FROM vehicle
                    INNER JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
                    INNER JOIN employee ON vehicle_group.fleet_manager_id = employee.id
                WHERE vehicle.company_id IN ({all_companies})
            """
        manager_df = pd.read_sql(manager_query, con)
    return vehicle_df, manager_df

def ensure_managers_exist(manager_df):
    with connect(localauth) as con, con.cursor() as cursor:
        for _, row in manager_df.iterrows():
            check_query = "SELECT COUNT(*) FROM Managers WHERE id = %s"
            insert_query = "INSERT INTO Managers (id, name) VALUES (%s, %s)"
            cursor.execute(check_query, (row['manager_id'],))
            if cursor.fetchone()[0] == 0:
                cursor.execute(insert_query, (row['manager_id'], row['manager']))
        con.commit()

def ensure_companies_exist(df):
    with connect(localauth) as con, con.cursor() as cursor:
        unique_companies = df[['company_id', 'company']].drop_duplicates()
        for _, row in unique_companies.iterrows():
            check_query = "SELECT COUNT(*) FROM Companies WHERE id = %s"
            insert_query = "INSERT INTO Companies (id, name) VALUES (%s, %s)"
            cursor.execute(check_query, (row['company_id'],))
            if cursor.fetchone()[0] == 0:
                cursor.execute(insert_query, (row['company_id'], row['company']))
        con.commit()

def ensure_centers_exist(df):
    with connect(localauth) as con, con.cursor() as cursor:
        unique_centers = df[['center_id', 'center']].drop_duplicates()
        for _, row in unique_centers.iterrows():
            check_query = "SELECT COUNT(*) FROM Centers WHERE id = %s"
            insert_query = "INSERT INTO Centers (id, name) VALUES (%s, %s)"
            cursor.execute(check_query, (row['center_id'],))
            if cursor.fetchone()[0] == 0:
                cursor.execute(insert_query, (row['center_id'], row['center']))
        con.commit()

def delete_absent_managers():
    with connect(kndauth) as con_knd, con_knd.cursor() as cursor_knd:
        cursor_knd.execute("""SELECT
                                e2.id as id
                            FROM
                                employee e
                            INNER JOIN 
                                employee e2 ON e2.id = e.fleet_manager_id
                            WHERE
                                e.geolocation_latitude IS NOT NULL
                                AND e.geolocation_longitude IS NOT NULL
                                AND e.status = 'active'
                                AND e.position_id in(6, 30)
                            GROUP BY
                                e2.id
                            ORDER BY
                                e2.id;""")
        knd_manager_ids = set([row[0] for row in cursor_knd.fetchall()])

    with connect(localauth) as con_local, con_local.cursor() as cursor_local:
        cursor_local.execute("SELECT id FROM Managers")
        local_manager_ids = set([row[0] for row in cursor_local.fetchall()])

        managers_to_delete = local_manager_ids - knd_manager_ids
        purged_managers_count = 0

        for manager_id in managers_to_delete:
            # with con_local.cursor() as cursor_local:
                # Check for dependencies in the Vehicles table
                cursor_local.execute("SELECT COUNT(*) FROM Vehicles WHERE manager_id = %s", (manager_id,))
                vehicles_count = cursor_local.fetchone()[0]

                # Check for dependencies in the Drivers table
                cursor_local.execute("SELECT COUNT(*) FROM Drivers WHERE manager_id = %s", (manager_id,))
                drivers_count = cursor_local.fetchone()[0]

                if vehicles_count == 0 and drivers_count == 0:
                # If no dependencies are found in either table, it's safe to delete the manager
                    delete_query = "DELETE FROM Managers WHERE id = %s"
                    cursor_local.execute(delete_query, (manager_id,))
                    purged_managers_count += 1  # Increment counter
                else:
                # Dependencies exist, so we skip deleting this manager
                    print(f"Skipping deletion of manager {manager_id} due to existing dependencies in Vehicles or Drivers tables.")
                con_local.commit()

        print(f"Completed checking and deleting absent managers from local database. Total managers purged: {purged_managers_count}.")

def insert_vehicle_data(df):
    with connect(localauth) as con, con.cursor() as cursor:

        # Ensure the 'date' column is filled with yesterday's date
        df['date'] = datetime.now()

        # Explicitly convert NaN values to None for 'manager_id' and 'manager' columns
        df['manager_id'] = df['manager_id'].apply(lambda x: None if pd.isna(x) else str(x))
        df['manager'] = df['manager'].apply(lambda x: None if pd.isna(x) else str(x))
        print(df.isna().sum())  # This will print the count of NaN values in each column
        
        for _, row in df.iterrows():
            query = """
            INSERT INTO Vehicles (kendra_id, plate, status, date, company_id, center_id, manager_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                plate = VALUES(plate),
                status = VALUES(status),
                date = VALUES(date),
                company_id = VALUES(company_id),
                center_id = VALUES(center_id),
                manager_id = VALUES(manager_id);
            """
            values = (
                row['kendra_id'], row['plate'], row['status'], row['date'],
                row['company_id'], row['center_id'], row['manager_id']
            )
            try:
                cursor.execute(query, values)
            except mysql.connector.Error as e:
                print(f"Error executing query: {e}")
        
        con.commit()
        print(f"Successful insertion of {len(df)} rows into Vehicles table.")

if __name__ == "__main__":
    df, manager_df = get_vehicle_stati()
    ensure_managers_exist(manager_df)
    delete_absent_managers()
    ensure_companies_exist(df)
    ensure_centers_exist(df)
    insert_vehicle_data(df)

