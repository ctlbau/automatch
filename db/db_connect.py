from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv('/Users/ctl/dev/automatch/.env')

kndauth = {
    "dialect": "mysql+pymysql",
    "username": os.environ['KND_USER'],
    "password": os.environ['KND_PASSWORD'],
    "host": os.environ['KND_HOST'],
    "dbname": os.environ['KND_NAME']
}

localauth_dev = {
    "dialect": "mysql+pymysql",
    "username": "ctl",
    "password": os.environ['MYSQL_CTL_PWD'],
    "host": "localhost",
    "dbname": "pulse_dev"
}

localauth_stg = {
    "dialect": "mysql+pymysql",
    "username": "ctl",
    "password": os.environ['MYSQL_CTL_PWD'],
    "host": "localhost",
    "dbname": "pulse_stg"
}

localauth_prod = {
    "dialect": "mysql+pymysql",
    "username": "ctl",
    "password": os.environ['MYSQL_CTL_PWD'],
    "host": "localhost",
    "dbname": "autopulse"
}

def get_url(auth):
    """Construct the database URL from auth dictionary."""
    return f"{auth['dialect']}://{auth['username']}:{auth['password']}@{auth['host']}/{auth['dbname']}"

def connect(auth):
    try:
        db_url = get_url(auth)
        engine = create_engine(db_url)
        # Attempt to connect to the database to validate connection parameters
        with engine.connect() as conn:
            pass  # Connection successful
        return engine
    except OperationalError as e:
        print(f"OperationalError: Could not connect to the database. {e}")
    except DBAPIError as e:
        print(f"DBAPIError: An error occurred with the database driver. {e}")
    except ImportError as e:
        print(f"ImportError: The database driver specified in the dialect is not installed. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

auroids = [5, 53, 56, 57, 59, 64, 123, 131, 132, 229, 234, 248, 62, 535]

cibeleids = [
    67, 122, 124, 125, 126, 127, 128, 129, 196, 197, 232, 238, 239, 246
]
gestionadoids = [
    74, 77, 231, 240, 287, 294, 295, 299, 304, 305, 306, 309, 613, 614,
    602, 555, 549, 536, 527
]
allids = auroids + cibeleids + gestionadoids

companies = {
    "auro" : auroids,
    "cibeles" : cibeleids,
    "gestionados" : gestionadoids,
    "all" : allids
}