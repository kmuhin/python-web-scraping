from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time, timezone
import csv
import json
from pprint import pprint
import requests
import sqlite3

"""
    The script gets data from bbc.com. Finds the data the cases of illness. It calculates the proportion of recovered.
    It saves data to files of types json and csv.
"""
# painting text
# \033[1;44;33m - bold(1) ; background(4) blue(4) ;foreground(3) yellow(3)
# \033[m - reset to the defaults
# 0 black
# 1 red
# 2 green
# 3 yellow
# 4 blue
# 5 magenta
# 6 cyan
# 7 white
# 9 default

now = datetime.now()
dbdate = datetime.combine(now, time(4, 0))

def dbcreate() -> object:
    conn = sqlite3.connect('bbc.covid19.sqlite3')
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
    return conn


    # debug
    # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    # print('schema: ')
    # pprint(cursor.fetchall())
def dbinsertregion(conn, data):
    ''' data=[region, regionISO]

        ['RUSSIA', 'RUS']
    '''
    cursor = conn.cursor()
    cursor.execute('insert or ignore into regions(region,regionISO) values(?,?)', data)
    cursor.execute('select id from regions where region=? AND regionISO=?', data)
    region_id = cursor.fetchall()[0][0]
    cursor.close()
    return region_id


def dbinsert(conn, data):
    '''data=[datetime, regions.region_id, cases, deaths]
       [datetime, 0, 1000, 0]
    '''
    cursor = conn.cursor()
    data[0] = data[0].replace(tzinfo=timezone.utc).timestamp()
    cursor.execute('insert or replace into CasesADay(date_int,region_id,cases,deaths) values(?,?,?,?)',
                   data)
    cursor.close()
    return cursor.lastrowid

def dbstatisticcountry(conn, country):
    cursor = conn.cursor()
    sqlstring = 'SELECT datetime(date_int,"unixepoch"),cases, deaths, region FROM CasesADAY' \
                ' LEFT JOIN regions ON CasesADAY.region_id=regions.id where regions.region=?'
    cursor.execute(sqlstring, [country])
    print()
    print(
        f'{"datetime":20} {"cases":>8} {"deaths":>6} {"country":>10} {"Cases":\u0394>7} {"Death":\u0394>7} {"rate":>5}')
    deathsbefore = -1
    casesbefore = -1
    for row in cursor.fetchall():
        deaths = row[2]
        cases = row[1]
        if deathsbefore == -1:
            deathsbefore = deaths
        if casesbefore == -1:
            casesbefore = cases
        Ddeaths = deaths - deathsbefore
        Dcases = cases - casesbefore
        deathsbefore = deaths
        casesbefore = cases
        rate = round(deaths / cases * 100, 2)
        print(f'{row[0]:20} {cases:8} {deaths:6} {row[3]:>10} {Dcases:7} {Ddeaths:7} {rate:5}')
    cursor.close()

def dbstatistic(conn):
    cursor = conn.cursor()
    print('DB statistic')
    print(' number of regions: ', end='')
    sqlstring = 'select count(1) from regions'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])

    print(' number of records cases: ', end='')
    sqlstring = 'select count(1) from CasesADAY'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])

    print(' number of cases with incorrect region: ', end='')
    sqlstring = 'SELECT count(1) FROM CasesADAY' \
                ' WHERE NOT EXISTS' \
                ' ( SELECT 1 FROM regions ' \
                '   WHERE regions.id = CasesADAY.region_id )'
    cursor.execute(sqlstring)
    print(cursor.fetchall()[0][0])

    print('TOP 10 CASES:')
    sqlstring = 'SELECT datetime(date_int,"unixepoch"),cases, deaths, region FROM CasesADAY' \
                ' LEFT JOIN regions ON CasesADAY.region_id=regions.id GROUP BY region ORDER BY cases DESC LIMIT 10'
    cursor.execute(sqlstring)
    pprint([i[0] for i in cursor.description])
    pprint(cursor.fetchall())

    dbstatisticcountry(conn, 'Russia')
    dbstatisticcountry(conn, 'US')
    cursor.close()

def dbtest():
    sqlstring = 'select max(id) from regions'
    cursor.execute(sqlstring)
    print(cursor.fetchall())

    sqlstring = 'select * from regions'
    cursor.execute(sqlstring)
    print('from regions:')
    pprint(cursor.fetchall())

    cursor.execute(
        'select datetime(date_int,"unixepoch"),* from CasesADAY LEFT JOIN regions ON CasesADAY.region_id=regions.id')
    # cursor.execute('select datetime(date_int,"unixepoch"),* from CasesADAY')
    print('from CasesADAY:')
    pprint(cursor.fetchall())

    sqlstring = 'INSERT INTO regions(region, regionISO)' \
                ' SELECT "AAA", "A" ' \
                ' WHERE NOT EXISTS (SELECT 1 from regions WHERE region="AAA" AND regioniso = "A");'
    cursor.execute(sqlstring)
    print(cursor.fetchall())
    cursor.close()


def dbcleanincoherent():
    sqlstring = 'SELECT count(rowid) FROM CasesADAY' \
                ' WHERE NOT EXISTS' \
                ' ( SELECT 1 FROM regions ' \
                '   WHERE regions.id = CasesADAY.region_id )'
    cursor.execute(sqlstring)
    print(cursor.fetchall())

    sqlstring = 'DELETE FROM CasesADAY ' \
                ' WHERE NOT EXISTS' \
                ' ( SELECT 1 FROM regions ' \
                '  WHERE regions.id = CasesADAY.region_id )'
    cursor.execute(sqlstring)
    print(cursor.fetchall())

    sqlstring = 'SELECT count(rowid) FROM CasesADAY' \
                ' WHERE NOT EXISTS' \
                ' ( SELECT 1 FROM regions ' \
                '   WHERE regions.id = CasesADAY.region_id )'
    cursor.execute(sqlstring)
    print(cursor.fetchall())
    cursor.close()

def printfooter():
    print('=' * 60)


def printheader():
    print('=' * 60)
    print(f'{"N":>3} {"region":25} {"ISO":3} {"cases":>8} {"deaths":>6} {"%":>8}')
    print('-' * 60)


tml_output = '{count:3} {region:25} {dataiso:3} {cases:8} {deaths:6} {percent:>8.2f}%'


def printrow(dataISO, count, **keywords):
    print(tml_output.format(count=count, region=keywords['region'], dataiso=dataISO, cases=keywords['cases'],
                            deaths=keywords['deaths'], percent=keywords['percent']))


def printrowfilter(dataISO, count, **keywords):
    print('\033[1;40;37m', end='')
    print(tml_output.format(count=count, region=keywords['region'], dataiso=dataISO, cases=keywords['cases'],
                            deaths=keywords['deaths'], percent=keywords['percent']), end='')
    print('\033[m')


def save2json(total_dict):
    with open(f'bbc.covid19.2.{now:%F}.json', 'w', encoding='utf-8') as f:
        json.dump(total_dict, f)


def save2csv(total_dict):
    # write list to csv
    with open(f'bbc.covid19.2.{now:%F}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['ISO', 'Region', 'Cases', 'Deaths', 'percent'])
        for k, v in total_dict.items():
            writer.writerow([k, v['region'], v['cases'], v['deaths'], v['percent']])


# Main

conn = dbcreate()

url_base = 'https://www.bbc.com/news/world-51235105'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
}

response = requests.get(url_base, headers=headers)
print(response.url)
print(response.elapsed)
print(response.encoding)
print(response.status_code)

for header in response.headers:
    print(f'{header:40}: {response.headers[header]}')
print()

with open(f'bbc.covid19.{now:%F}.html', 'wb') as f:
    f.write(response.content)

soap = BeautifulSoup(response.text, "html.parser")
filter_tag_tbody = soap.findAll('tbody')
total_list = {}
# filter_tag_tbody_text = filter_tag_tbody[0].text
printheader()
count = 0
# <div class="pocket pocket--less gel-long-primer"> <table class="core gel-brevier"> <tbody>
if filter_tag_tbody[0]:
    for child in filter_tag_tbody[0]:
        if child.name:
            # <tr class="core__row" data-iso="USA">
            #    <td class="core__region">
            #           USA
            #    </td>
            #    <td class="core__value">
            #           104,688
            #    </td>
            #    <td class="core__value">
            #           1,707
            #    </td>
            # </tr>
            # search tag <td>
            dataISO = child.attrs['data-iso']
            tags_td = child.find_all('td')
            if tags_td:
                region = tags_td[0].text.strip()
                cases = 0
                deaths = 0
                percent = 0
                try:
                    cases = int(tags_td[3].text.strip().replace(',', ''))
                    deaths = int(tags_td[1].text.strip().replace(',', ''))
                except:
                    continue
                regionid = dbinsertregion(conn, [region, dataISO])
                dbinsert(conn, [dbdate, regionid, cases, deaths])
                if cases != 0:
                    percent = round(deaths / cases * 100, 2)
                total_list[dataISO] = {'region': region, 'cases': cases, 'deaths': deaths, 'percent': percent}
                if region.upper() == 'RUSSIA':
                    printrowfilter(dataISO, count, **total_list[dataISO])
                elif count < 10:
                    printrow(dataISO, count, **total_list[dataISO])
                count += 1
conn.commit()
printfooter()
print(f'count: {len(total_list)}')
cases_min = 10000
print('\nregions with cases > ', cases_min, ':')
# select region where cases > cases_min
list_sort_percent =[i for i in total_list.items() if i[1]['cases'] >= cases_min]

save2json(total_list)
save2csv(total_list)

list_sort_percent = sorted(list_sort_percent, key=lambda item: item[1]['percent'])
printheader()
count = 0
for row in list_sort_percent:
    region = row[1]['region']
    cases = row[1]['cases']
    deaths = row[1]['deaths']
    percent = row[1]['percent']
    dataISO = row[0]
    if region.upper() == 'RUSSIA':
        printrowfilter(dataISO, count, **row[1])
    else:
        printrow(dataISO, count, **row[1])
    count += 1
printfooter()
print(f'count: {len(list_sort_percent)}')
dbstatistic(conn)
conn.close()
