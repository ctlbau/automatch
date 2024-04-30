import os
import pandas as pd
from ..db_connect import localauth_dev, localauth_stg, localauth_prod, companies, connect

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from db.assignments.db_support import create_vehicle_shifts

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
    shifts = create_vehicle_shifts()
    shifts['date'] = pd.to_datetime(shifts['date'])
    shifts['manana'] = shifts['manana'].astype(int)
    shifts['tarde'] = shifts['tarde'].astype(int)
    shifts['l_j_40h'] = shifts['l_j_40h'].astype(int)
    shifts['tp_v_d'] = shifts['tp_v_d'].astype(int)
    shifts['tp_l_v'] = shifts['tp_l_v'].astype(int)
    shifts['l_j'] = shifts['l_j'].astype(int)
    shifts['turno_completo'] = shifts['turno_completo'].astype(int)
    shifts['number_of_drivers'] = shifts['number_of_drivers'].astype(int)
    
    engine = connect(localauth)

    sql = text("""
    INSERT INTO VehicleShiftsHistorical
        (date, plate, manager, center, number_of_drivers, manana, tarde, tp_v_d, tp_l_v, l_j, l_j_40h, turno_completo)
    VALUES
        (:date, :plate, :manager, :center, :number_of_drivers, :manana, :tarde, :tp_v_d, :tp_l_v, :l_j, :l_j_40h, :turno_completo)
    ON DUPLICATE KEY UPDATE
        date = VALUES(date),
        plate = VALUES(plate),
        manager = VALUES(manager),
        center = VALUES(center),
        number_of_drivers = VALUES(number_of_drivers),
        manana = VALUES(manana),
        tarde = VALUES(tarde),
        tp_v_d = VALUES(tp_v_d),
        tp_l_v = VALUES(tp_l_v),
        l_j = VALUES(l_j),
        l_j_40h = VALUES(l_j_40h),
        turno_completo = VALUES(turno_completo);
    """)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                for index, row in shifts.iterrows():
                    conn.execute(sql, row.to_dict())
                transaction.commit()
                print(f"Inserted {len(shifts)} rows into VehicleShiftsHistorical table")
            except Exception as e:
                transaction.rollback()
                print("Transaction failed and was rolled back.")
                print(e)
    except SQLAlchemyError as e:
        print("Failed to connect or execute transaction.")
        print(e)    

if __name__ == '__main__':
    fetch_prepare_and_insert_vehicle_shifts_snapshot()

