import os
import pymysql
import logging
import pandas as pd
import time
from datetime import date

from db.db_connect import connect, localauth, companies

# kndauth = {
#     "DB_HOST" : os.environ['KND_HOST'],
#     "DB_USER" : os.environ['KND_USER'],
#     "DB_PASSWORD" : os.environ['KND_PASSWORD'],
#     "DB_NAME" : os.environ['KND_NAME']
#     }

# localauth = {
#     "DB_HOST" : "localhost",
#     "DB_USER" : "ctl",
#     "DB_PASSWORD" : os.environ['MYSQL_PASSWORD'],
#     "DB_NAME" : "autopulse"
#     }

# auroids = [5, 53, 56, 57, 59, 64, 123, 131, 132, 229, 234, 248, 62, 535]

# cibeleids = [
#     67, 122, 124, 125, 126, 127, 128, 129, 196, 197, 232, 238, 239, 246
# ]
# gestionadoids = [
#     74, 77, 231, 240, 287, 294, 295, 299, 304, 305, 306, 309, 613, 614,
#     602, 555, 549, 536, 527
# ]
# allids = auroids + cibeleids + gestionadoids

# companies = {
#     "auro" : auroids,
#     "cibeles" : cibeleids,
#     "gestionados" : gestionadoids,
#     "all" : allids
# }


# def connect(auth):
#     con = None
#     while True:
#         try:
#             con = pymysql.connect(host=auth['DB_HOST'],
#                                   user=auth['DB_USER'],
#                                   password=auth['DB_PASSWORD'],
#                                   db=auth['DB_NAME'])
#             break
#         except Exception as e:
#             logging.warning(f"Failed to connect to {auth['DB_HOST']}: {e}")
#             time.sleep(1)
#     return con

def fetch_managers():
    query = """
    SELECT
        M.id,
        M.name
    FROM
        Managers AS M;
    """
    con = None
    try:
        con = connect(localauth)
        with con.cursor() as cursor:
            cursor.execute(query)
            managers = pd.DataFrame(cursor.fetchall(), columns=['id', 'name'])
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        managers = pd.DataFrame(columns=['id', 'name'])
    finally:
        if con:
            con.close()
    return managers

def fetch_statuses():
    query = """
    SELECT DISTINCT
        V.status
    FROM
        Vehicles AS V;
    """
    con = None
    try:
        con = connect(localauth)
        with con.cursor() as cursor:
            cursor.execute(query)
            statuses = pd.DataFrame(cursor.fetchall(), columns=['status'])
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        statuses = pd.DataFrame(columns=['status'])
    finally:
       if con:
           con.close()
    return statuses

def fetch_date_range():
    query = """
    SELECT
        MIN(V.date) AS min_date,
        MAX(V.date) AS max_date
    FROM
        Vehicles AS V;
    """
    try:
        con = connect(localauth)
        with con.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            min_date, max_date = result
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        min_date, max_date = None, None
    finally:
        if con:
            con.close()
    return min_date, max_date

def fetch_plates():
    query = """
    SELECT
        DISTINCT V.plate
    FROM
        Vehicles AS V;
    """
    try:
        con = connect(localauth)
        with con.cursor() as cursor:
            cursor.execute(query)
            plates = pd.DataFrame(cursor.fetchall(), columns=['plate'])
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        plates = pd.DataFrame(columns=['plate'])
    finally:
        if con:
            con.close()
    return plates

def fetch_vehicles(company=companies["all"], from_date=None, to_date=None):
    company = companies[company]
    con = connect(localauth)

    # Constructing date condition
    date_condition = ""
    if from_date and to_date:
        date_condition = f"AND V.date BETWEEN '{from_date}' AND '{to_date}'"
    elif from_date:
        date_condition = f"AND V.date >= '{from_date}'"
    elif to_date:
        date_condition = f"AND V.date <= '{to_date}'"

    query = f"""
    SELECT
        V.kendra_id,
        V.date,
        V.plate,
        V.status,
        M.name as manager,
        C.name as company,
        Ce.name as center
    FROM
        Vehicles AS V
    INNER JOIN
        Companies AS C ON V.company_id = C.id
    INNER JOIN
        Centers AS Ce ON V.center_id = Ce.id
    LEFT JOIN
        Managers AS M ON V.manager_id = M.id
    WHERE
        V.company_id IN ({', '.join(map(str, company))})
        {date_condition};
    """
    try:
        with con.cursor() as cursor:
            cursor.execute(query)
            df = pd.DataFrame(cursor.fetchall())
            df.columns = ['kendra_id', 'date', 'plate', 'status', 'manager', 'company', 'center']
            pd.to_datetime(df['date'])
    except Exception as e:
        logging.error(f"Error executing query: {e}")
    finally:
        if con:
            con.close()
    return df

def select_plate(plate, from_date=None, to_date=None):
  if not plate:
      return pd.DataFrame(columns=['date', 'status'])
  date_condition = ""
  params = [plate]
  if from_date and to_date:
      date_condition = "AND date BETWEEN %s AND %s"
      params.extend([date.fromisoformat(from_date), date.fromisoformat(to_date)])
  elif from_date:
      date_condition = "AND date >= %s"
      params.append(date.fromisoformat(from_date))
  elif to_date:
      date_condition = "AND date <= %s"
      params.append(date.fromisoformat(to_date))

  query = f"""
  SELECT
      date,
      status
  FROM
      Vehicles
  WHERE
      plate = %s
      {date_condition};
  """
  df = pd.DataFrame(columns=['date', 'status']) # Assign a default value to df
  try:
      con = connect(localauth)
      with con.cursor() as cursor:
          cursor.execute(query, params)
          df = pd.DataFrame(cursor.fetchall(), columns=['date', 'status'])
          df['date'] = pd.to_datetime(df['date'])
  except Exception as e:
      logging.error(f"Error executing query: {e}")
  finally:
      if con:
          con.close()
  return df

def get_vehicle_stati():
    con = connect(auth)

    auroids = [5, 53, 56, 57, 59, 64, 123, 131, 132, 229, 234, 248, 62, 535]
    cibeleids = [67, 122, 124, 125, 126, 127, 128, 129, 196, 197, 232, 238, 239, 246]
    gestionadoids = [74, 77, 231, 240, 287, 294, 295, 299, 304, 305, 306, 309, 613, 614, 602, 555, 549, 536, 527]

    all_ids = auroids + cibeleids + gestionadoids
    allcompanies = ', '.join(map(str, all_ids))

    query = f"""
        SELECT
            vehicle.id,
            vehicle.license_plate_number AS plate,
            vehicle.status,
            employee.id as manager_id,
            CONCAT(employee.first_name, ' ', employee.last_name) AS manager,
            vehicle.company_id,
            company.name AS company,
            center.id AS center_id,
            center.name AS center
        FROM vehicle
            INNER JOIN company ON vehicle.company_id = company.id
            INNER JOIN center ON vehicle.operating_center_id = center.id
            INNER JOIN vehicle_group ON vehicle.vehicle_group_id = vehicle_group.id
            INNER JOIN employee ON vehicle_group.fleet_manager_id = employee.id
        WHERE vehicle.company_id IN({allcompanies})
    """
    # print(query)
    with con.cursor() as cursor:
        cursor.execute(query)
        df = pd.DataFrame(cursor.fetchall())
    return df