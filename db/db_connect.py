from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

thisdir = os.path.dirname(__file__)
envdir = os.path.dirname(thisdir)

load_dotenv(os.path.join(envdir, '.env'))

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
