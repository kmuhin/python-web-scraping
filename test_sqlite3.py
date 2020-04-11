from datetime import datetime, date, time, timezone
from pprint import pprint
import sqlite3


def s():
    cursor.execute('select * from regions')
    print('from regions:')
    pprint(cursor.fetchall())
    cursor.execute(
        'select datetime(date_int,"unixepoch"),* from CasesADAY LEFT JOIN regions ON CasesADAY.region_id=regions.id')
    # cursor.execute('select datetime(date_int,"unixepoch"),* from CasesADAY')
    print('from CasesADAY:')
    pprint(cursor.fetchall())

def dbinsertregion(conn, data):
    cursor = conn.cursor()
    cursor.execute('insert or ignore into regions(region,regionISO) values(?,?)', data)
    region_id = cursor.lastrowid
    cursor.close()
    return  region_id


def dbinsert(conn, data):
    cursor = conn.cursor()
    cursor.execute('insert or replace into CasesADay(date_int,region_id,cases,deaths) values(?,?,15,0)',
                   [data[0].replace(tzinfo=timezone.utc).timestamp(), data[1]])
    cursor.close()
    return cursor.lastrowid


conn = sqlite3.connect('test.sqlite3')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS regions(
               id INTEGER PRIMARY KEY, 
               region TEXT NOT NULL, 
               regionISO TEXT NOT NULL,
               UNIQUE(regionISO)
               )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS CasesADay(
               date_int INT NOT NULL, 
               region_id INT NOT NULL, 
               cases INT,
               deaths INT,
               UNIQUE(date_int, region_id),
               FOREIGN KEY (region_id) REFERENCES regions(id)
               )''')

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('schema: ')
pprint(cursor.fetchall())

cursor.execute('select * from regions')
data = cursor.fetchall()
dataiso = {i[2]: i[0:2] for i in data}
today = datetime.combine(date.today(),time(4,0))

if 'RUS' in dataiso.keys():
    region_id = dataiso['RUS'][0]
else:
    region_id = dbinsertregion(conn,['RUSSIA', 'RUS'])


dbinsert(conn, [today, region_id])

if 'USA' in dataiso.keys():
    region_id = dataiso['USA'][0]
else:
    region_id = dbinsertregion(conn, ['USA', 'USA'])


dbinsert(conn, [today, region_id])

s()
conn.commit()
conn.close()
