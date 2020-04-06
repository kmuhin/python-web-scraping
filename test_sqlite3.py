import sqlite3


def s():
    cursor.execute('select * from CasesADAY')
    print(cursor.fetchall())
    cursor.execute('select * from regions')
    print(cursor.fetchall())

conn = sqlite3.connect('test.sqlite3')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS regions(
               id INTEGER PRIMARY KEY, 
               region TEXT NOT NULL, 
               regionISO TEXT NOT NULL,
               UNIQUE(regionISO)
               )''')

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

cursor.execute('''CREATE TABLE IF NOT EXISTS CasesADay(
               date_int INT NOT NULL, 
               region_id INT NOT NULL, 
               cases INT,
               deaths INT,
               FOREIGN KEY (region_id) REFERENCES regions(id)
               )''')

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

cursor.execute('select * from regions')
data = cursor.fetchall()
cursor.execute('insert or ignore into regions(region,regionISO) values("RUSSIA","RUS")')
print(cursor.lastrowid)
cursor.execute('insert or ignore into regions(region,regionISO) values("USA","USA")')
print(cursor.lastrowid)
cursor.execute('insert into CasesADay(date_int,region_id) values(0,1)')

s()
conn.commit()
conn.close()