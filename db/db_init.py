from db_connect import *
from sqlalchemy import text

def create_autopulse_db():
    engine = connect({**localauth, 'database': None})
    if engine:
        with engine.begin() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS autopulse;"))
        localauth['database'] = 'autopulse'  

def create_managers_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS Managers(
                    id INT PRIMARY KEY,
                    name VARCHAR(50)
                );
            """))

def create_company_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS Companies (
                    id INT PRIMARY KEY,
                    name VARCHAR(60)
                );
            """))


def create_center_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS Centers (
                    id INT PRIMARY KEY,
                    name VARCHAR(70)
                );
            """))

def create_shifts_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS Shifts (
                    id INT PRIMARY KEY,
                    name VARCHAR(70)
                );
            """))

def create_provinces_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS Provinces (
                    id INT PRIMARY KEY,
                    name VARCHAR(100)
                );
            """))


def create_exchange_location_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ExchangeLocations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL
                );
            """))

def create_companies_centers_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS CompaniesCenters (
                    company_id INT,
                    center_id INT,
                    PRIMARY KEY (company_id, center_id),
                    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
                    FOREIGN KEY (center_id) REFERENCES Centers(id) ON DELETE CASCADE
                );
            """))


def create_vehicle_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
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
            """))

def create_drivers_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
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
                    FOREIGN KEY (manager_id) REFERENCES Managers(id) ON DELETE CASCADE,
                    FOREIGN KEY (shift_id) REFERENCES Shifts(id) ON DELETE CASCADE
                );
            """))


def create_drivers_vehicles_table():
    engine = connect(localauth)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS DriversVehicles (
                    driver_id INT,
                    vehicle_id INT,
                    exchange_location_id INT,
                    PRIMARY KEY (driver_id, vehicle_id),
                    FOREIGN KEY (driver_id) REFERENCES Drivers(kendra_id) ON DELETE CASCADE,
                    FOREIGN KEY (vehicle_id) REFERENCES Vehicles(kendra_id) ON DELETE CASCADE,
                    FOREIGN KEY (exchange_location_id) REFERENCES ExchangeLocations(id)
                );
            """))


# Main execution block
if __name__ == "__main__":
    create_autopulse_db()
    create_managers_table()
    create_exchange_location_table()
    create_company_table()
    create_center_table()
    create_companies_centers_table()
    create_vehicle_table()
    create_provinces_table()
    create_shifts_table()
    create_drivers_table()
    create_drivers_vehicles_table()
