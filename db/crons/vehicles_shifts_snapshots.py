import os
import pandas as pd
from ..db_connect import localauth_dev, localauth_stg, localauth_prod, companies, connect

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from db.blockbuster.db_support import fetch_vehicle_shifts

from datetime import datetime
from dotenv import load_dotenv

thisdir = os.path.dirname(__file__)
parentdir = os.path.dirname(thisdir)
envdir = os.path.dirname(parentdir)

load_dotenv(os.path.join(envdir, '.env'))

app_env = os.getenv("APP_ENV", "dev")
if app_env == 'stg':
    localauth = localauth_stg
elif app_env == 'dev':
    localauth = localauth_dev
else:
    localauth = localauth_prod


def fetch_prepare_and_insert_vehicle_shifts_snapshot():
    shifts = fetch_vehicle_shifts()
    required_columns = ['plate', 'manana', 'tarde', 'l_j_40h', 'tp_v_d', 'number_of_drivers', 'manager', 'center']
    shifts.rename(columns={
        'Mañana': 'manana',
        'Tarde': 'tarde',
        'L-J_(40h)': 'l_j_40h',
        'TP-V-D': 'tp_v_d'
    }, inplace=True)
    shifts = shifts[required_columns]
    shifts['date'] = datetime.today().date()
    shifts['manana'] = shifts['manana'].astype(int)
    shifts['tarde'] = shifts['tarde'].astype(int)
    shifts['l_j_40h'] = shifts['l_j_40h'].astype(int)
    shifts['tp_v_d'] = shifts['tp_v_d'].astype(int)
    shifts['number_of_drivers'] = shifts['number_of_drivers'].astype(int)
    
    engine = connect(localauth)

    sql = text("""
    INSERT INTO VehicleShiftHistorical
        (date, plate, manager, center, number_of_drivers, manana, tarde, l_j_40h, tp_v_d)
    VALUES
        (:date, :plate, :manager, :center, :number_of_drivers, :manana, :tarde, :l_j_40h, :tp_v_d)
    ON DUPLICATE KEY UPDATE
        manager = VALUES(manager),
        center = VALUES(center),
        number_of_drivers = VALUES(number_of_drivers),
        manana = VALUES(manana),
        tarde = VALUES(tarde),
        l_j_40h = VALUES(l_j_40h),
        tp_v_d = VALUES(tp_v_d);
    """)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for index, row in shifts.iterrows():
                    conn.execute(sql, row.to_dict())
                transaction.commit()
                print(f"Inserted {len(shifts)} rows into VehicleShiftHistorical table")
            except Exception as e:
                transaction.rollback()
                print("Transaction failed and was rolled back.")
                print(e)
    except SQLAlchemyError as e:
        print("Failed to connect or execute transaction.")
        print(e)    

if __name__ == '__main__':
    fetch_prepare_and_insert_vehicle_shifts_snapshot()

