from db.db_connect import connect, localauth, kndauth

def fetch_and_insert_managers(kndauth, localauth):
    select_query = """SELECT
                        e2.id as kendra_id,
                        CONCAT(e2.first_name, ' ', e2.last_name) AS name
                    FROM
                        employee e
                        INNER JOIN employee e2 ON e2.id = e.fleet_manager_id                        
                    WHERE
                        e.geolocation_latitude IS NOT NULL
                        AND e.geolocation_longitude IS NOT NULL
                        AND e.status = 'active'
                        AND e.position_id in(6, 30)
                    GROUP BY
                        e2.id
                    ORDER BY 
                        e2.id;"""
    insert_query = """INSERT IGNORE INTO Managers (id, name) VALUES (%s, %s);"""

    with connect(kndauth) as knd_conn:
        with knd_conn.cursor() as knd_cursor:
            knd_cursor.execute(select_query)
            managers = knd_cursor.fetchall()
    
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.executemany(insert_query, managers)
            local_conn.commit()
            print("Managers data inserted successfully")

def fetch_and_insert_shift_data(kndauth, localauth):
    select_query = """SELECT s.id AS shift_id, s.name AS name FROM shift s ORDER BY s.id;"""
    insert_query = """INSERT IGNORE INTO Shifts (id, name) VALUES (%s, %s);"""

    with connect(kndauth) as knd_conn:
        with knd_conn.cursor() as knd_cursor:
            knd_cursor.execute(select_query)
            shifts = knd_cursor.fetchall()
    
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.executemany(insert_query, shifts)
            local_conn.commit()
            print("Shifts data inserted successfully")

def fetch_and_insert_provinces(kndauth, localauth):
    select_query = """SELECT p.id, p.name FROM province p ORDER BY p.id;"""
    insert_query = """INSERT IGNORE INTO Provinces (id, name) VALUES (%s, %s);"""

    with connect(kndauth) as knd_conn:
        with knd_conn.cursor() as knd_cursor:
            knd_cursor.execute(select_query)
            provinces = knd_cursor.fetchall()
    
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.executemany(insert_query, provinces)
            local_conn.commit()
            print("Provinces data inserted successfully")

def fetch_and_insert_drivers(kndauth, localauth):
    select_query = """
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
        e.geolocation_latitude IS NOT NULL
        AND e.geolocation_longitude IS NOT NULL
        AND e.status = 'active'
        AND(es.end_date IS NULL
            OR es.end_date >= date(now()))
        AND es.start_date <= date(now())
        AND e.position_id in(6, 30)
        AND es.deleted_at IS NULL
        AND a.province_id in(28)
    ORDER BY
        e.id;"""
    insert_query = """INSERT INTO Drivers (kendra_id, name, street, city, country, zip_code, lat, lng, province_id, manager_id, shift_id) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
    ON DUPLICATE KEY UPDATE 
    name=VALUES(name), street=VALUES(street), city=VALUES(city), country=VALUES(country), zip_code=VALUES(zip_code), 
    lat=VALUES(lat), lng=VALUES(lng), province_id=VALUES(province_id), manager_id=VALUES(manager_id), shift_id=VALUES(shift_id);"""

    with connect(kndauth) as knd_conn:
        with knd_conn.cursor() as knd_cursor:
            knd_cursor.execute(select_query)
            drivers = knd_cursor.fetchall()
    
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            local_cursor.executemany(insert_query, drivers)
            local_conn.commit()
            print("Drivers data inserted successfully")

def fetch_and_insert_drivers_vehicles(kndauth, localauth):
    select_query = """
    SELECT
        e.id AS driver_id,
        v.id AS vehicle_id
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
        AND e.geolocation_latitude IS NOT NULL
        AND e.geolocation_longitude IS NOT NULL
        AND e.status = 'active'
    ORDER BY
        e.id, v.id;
    """
    insert_query = """
    INSERT INTO DriversVehicles (driver_id, vehicle_id)
    SELECT * FROM (SELECT %s AS driver_id, %s AS vehicle_id) AS tmp
    WHERE EXISTS (
        SELECT 1 FROM Drivers d WHERE d.kendra_id = tmp.driver_id
    ) AND EXISTS (
        SELECT 1 FROM Vehicles v WHERE v.kendra_id = tmp.vehicle_id
    )
    ON DUPLICATE KEY UPDATE driver_id=VALUES(driver_id), vehicle_id=VALUES(vehicle_id);
    """

    with connect(kndauth) as knd_conn:
        with knd_conn.cursor() as knd_cursor:
            knd_cursor.execute(select_query)
            drivers_vehicles = knd_cursor.fetchall()
    
    with connect(localauth) as local_conn:
        with local_conn.cursor() as local_cursor:
            for driver_vehicle in drivers_vehicles:
                local_cursor.execute(insert_query, driver_vehicle)
            local_conn.commit()
            print("DriversVehicles data inserted successfully")

if __name__ == "__main__":
    fetch_and_insert_managers(kndauth, localauth)
    fetch_and_insert_shift_data(kndauth, localauth)
    fetch_and_insert_provinces(kndauth, localauth)
    fetch_and_insert_drivers(kndauth, localauth)
    fetch_and_insert_drivers_vehicles(kndauth, localauth)

# def fetch_and_insert_vehicles(kndauth, localauth):
#     all_ids = companies['all']
#     all_companies = ', '.join(map(str, all_ids))
#     select_query = f"""
#             SELECT
#                 vehicle.id AS kendra_id,
#                 vehicle.license_plate_number AS plate,
#                 vehicle.status AS status,
#                 employee.id as manager_id,
#                 CONCAT(employee.first_name, ' ', employee.last_name) AS manager,
#                 vehicle.company_id AS company_id,
#                 company.name AS company,
#                 center.id AS center_id,
#                 center.name AS center
#             FROM vehicle
#                 INNER JOIN company ON vehicle.company_id = company.id
#                 INNER JOIN center ON vehicle.operating_center_id = center.id
#                 LEFT JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
#                 LEFT JOIN employee ON vehicle_group.fleet_manager_id = employee.id
#             WHERE vehicle.company_id IN ({all_companies})
#         """
#     insert_query = """INSERT INTO Vehicles (kendra_id, plate, status, manager_id, manager, company_id, company, center_id, center) 
#     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
#     ON DUPLICATE KEY UPDATE 
#     plate=VALUES(plate), status=VALUES(status), manager_id=VALUES(manager_id), manager=VALUES(manager), company_id=VALUES(company_id), 
#     company=VALUES(company), center_id=VALUES(center_id), center=VALUES(center);"""

#     with connect(kndauth) as knd_conn:
#         with knd_conn.cursor() as knd_cursor:
#             knd_cursor.execute(select_query)
#             vehicles = knd_cursor.fetchall()
    
#     with connect(localauth) as local_conn:
#         with local_conn.cursor() as local_cursor:
#             local_cursor.executemany(insert_query, vehicles)
#             local_conn.commit()
#             print("Vehicles data inserted successfully")