from db_connect import *

def connect(auth):
    while True:
        try:
            return pymysql.connect(
                host=auth['host'],
                user=auth['user'],
                password=auth['password'],
                database=auth.get('database', None),
                # autocommit=True
            )
        except pymysql.MySQLError as e:
            print(f"Failed to connect to MySQL: {e}")
            sleep(1)

def create_autopulse_db():
    with connect({**localauth, 'database': None}) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS autopulse;")
    localauth['database'] = 'autopulse'

def create_managers_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Managers(
                    id INT PRIMARY KEY,
                    name VARCHAR(50)
                );
            """)

def create_company_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Companies (
                    id INT PRIMARY KEY,
                    name VARCHAR(60)
                );
            """)

def create_center_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Centers (
                    id INT PRIMARY KEY,
                    name VARCHAR(70)
                );
            """)

def create_companies_centers_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS CompaniesCenters (
                    company_id INT,
                    center_id INT,
                    PRIMARY KEY (company_id, center_id),
                    FOREIGN KEY (company_id) REFERENCES Companies(id),
                    FOREIGN KEY (center_id) REFERENCES Centers(id)
                );
            """)

def create_vehicle_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Vehicles (
                    kendra_id INT NOT NULL,
                    plate VARCHAR(10) NOT NULL,
                    status VARCHAR(17) NOT NULL,
                    date DATE NOT NULL,
                    company_id INT NOT NULL,
                    center_id INT NOT NULL,
                    manager_id INT,
                    PRIMARY KEY (date, plate),
                    INDEX (kendra_id),
                    FOREIGN KEY (company_id) REFERENCES Companies(id),
                    FOREIGN KEY (center_id) REFERENCES Centers(id),
                    FOREIGN KEY (manager_id) REFERENCES Managers(id)
                );
            """)


def create_drivers_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Drivers (
                    kendra_id INT PRIMARY KEY,
                    name VARCHAR(100),
                    street VARCHAR(255),
                    city VARCHAR(100),
                    country VARCHAR(100),
                    zip_code VARCHAR(20),
                    lat DOUBLE,
                    lng DOUBLE,
                    province_id INT,
                    manager_id INT,
                    shift_id INT,
                    FOREIGN KEY (province_id) REFERENCES Provinces(id),
                    FOREIGN KEY (manager_id) REFERENCES Managers(id),
                    FOREIGN KEY (shift_id) REFERENCES Shifts(id)
                );
            """)

def create_shifts_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Shifts (
                    id INT PRIMARY KEY,
                    name VARCHAR(50)
                );
            """)

def create_provinces_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Provinces (
                    id INT PRIMARY KEY,
                    name VARCHAR(100)
                );
            """)

def create_drivers_vehicles_table():
    with connect(localauth) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DriversVehicles (
                    driver_id INT,
                    vehicle_id INT,
                    PRIMARY KEY (driver_id, vehicle_id),
                    FOREIGN KEY (driver_id) REFERENCES Drivers(kendra_id),
                    FOREIGN KEY (vehicle_id) REFERENCES Vehicles(kendra_id)
                );
            """)

# Main execution block
if __name__ == "__main__":
    create_autopulse_db()
    create_managers_table()
    create_company_table()
    create_center_table()
    create_companies_centers_table()
    create_vehicle_table()
    create_provinces_table()
    create_shifts_table()
    create_drivers_table()
    create_drivers_vehicles_table()
