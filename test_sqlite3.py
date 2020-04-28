from datetime import datetime, date, time, timezone
from pprint import pprint
import sqlite3


def printdata():
    print(' number of regions: ', end='')
    sqlstring = 'select count(1) from regions'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])

    cursor.execute('select * from regions')
    print('from regions:')
    pprint([i[0] for i in cursor.description])
    pprint(cursor.fetchall())

    print(' number of records cases: ', end='')
    sqlstring = 'select count(1) from CasesADAY'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])

    cursor.execute(
        'select datetime(date_int,"unixepoch"),* from CasesADAY'
        ' LEFT JOIN regions ON CasesADAY.region_id=regions.id LIMIT 100')
    # cursor.execute('select datetime(date_int,"unixepoch"),* from CasesADAY')
    print('from CasesADAY:')
    pprint(cursor.fetchall())

    print(' number of cases with incorrect region: ', end='')
    sqlstring = 'SELECT count(1) FROM CasesADAY' \
                ' WHERE NOT EXISTS' \
                ' ( SELECT 1 FROM regions ' \
                '   WHERE regions.id = CasesADAY.region_id )'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])


def dbinsertregion(conn, data):
    cursor = conn.cursor()
    cursor.execute('insert or replace into regions(region,regionISO) values(?,?)', data)
    region_id = cursor.lastrowid
    cursor.close()
    return region_id


def dbinsert(conn, data):
    cursor = conn.cursor()
    data[0] = data[0].replace(tzinfo=timezone.utc).timestamp()
    cursor.execute('insert or replace into CasesADay(date_int,region_id, cases,deaths) values(?,?,?,?)', data)
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
today = datetime.combine(date.today(), time(4, 0))


def addcase(region, regionISO, cases, deaths):
    if regionISO in dataiso.keys():
        region_id = dataiso[regionISO][0]
    else:
        region_id = dbinsertregion(conn, [region, regionISO])
    dbinsert(conn, [today, region_id, cases, deaths])


addcase('RUSSIA', 'RUS', 100, 0)
addcase('US', 'USA', 200, 0)

printdata()
conn.commit()
conn.close()
