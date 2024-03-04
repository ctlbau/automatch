import pymysql
from time import sleep
import os

kndauth = {
    "host" : os.environ['KND_HOST'],
    "user" : os.environ['KND_USER'],
    "password" : os.environ['KND_PASSWORD'],
    "database" : os.environ['KND_NAME']
    }

localauth = {
    "host": "localhost",
    "user": "root",
    "password": os.environ['MYSQL_ROOT_PWD'],
    "database": "autopulse"
}

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