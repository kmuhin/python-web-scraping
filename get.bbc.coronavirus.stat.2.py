from bs4 import BeautifulSoup
import datetime
import csv
import json
import requests
import sqlite3

"""
    The script get data from bbc.com. Finds the data the cases of illness. It calculates the proportion of recovered.
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

now = datetime.datetime.now()


def createDB():
    conn = sqlite3.connect('bbc.covid19.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS regions('
                   'id INT PRIMARY KEY, '
                   'region TEXT NOT NULL, '
                   'regionISO TEXT,'
                   'UNIQUE(regionISO)'
                   ')')
    cursor.execute('CREATE TABLE IF NOT EXISTS CasesADay('
                   'date_int INT NOT NULL, '
                   'region_id integer NOT NULL, '
                   'cases INT,'
                   'deaths INT'
                   'FOREIGN KEY (region_id) PREFERENCES  regions(id)'
                   ')')
def dbinsert(conn, region):
    sql = ''' INSERT OR IGNORE INTO regions (region, regionISO)
              VALUES(?,?)'''
    cur = conn.cursor()
    cur.extcute(sql, region)
    return cur.lastrowid

def printfooter():
    print('=' * 60)


def printheader():
    print('=' * 60)
    print(f'{"N":>3} {"region":25} {"ISO":3} {"cases":>8} {"deaths":>6} {"%":>8}')
    print('-' * 60)


tml_output = '{count:3} {region:25} {dataiso:3} {cases:8} {deaths:6} {percent:>8.2f}%'


def printrow(count, region, dataiso, cases, deaths, percent):
    print(tml_output.format(count=count, region=region, dataiso=dataiso, cases=cases, deaths=deaths, percent=percent))


def printrowfilter(count, region, dataiso, cases, deaths, percent):
    print('\033[1;40;37m', end='')
    print(tml_output.format(count=count, region=region, dataiso=dataiso, cases=cases, deaths=deaths, percent=percent), end='')
    print('\033[m')


def save2json(total_list):
    # convert list to dictionary
    # x[0] - Region
    # x[1:4] - cases,death,percent
    total_dict = {x[0]: x[1:4] for x in total_list}
    # write dictionary to file
    # use json because it saves correct data and converts quotes. in the future it will allow the use of json.loads.
    with open(f'bbc.covid19.{now:%F}.json', 'w', encoding='utf-8') as f:
        json.dump(total_dict, f)


def save2csv(total_list):
    # write list to csv
    with open(f'bbc.covid19.{now:%F}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Region', 'Cases', 'Deaths', 'percent'])
        for row in total_list:
            writer.writerow(row)


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
total_list = []
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
                    cases = int(tags_td[1].text.strip().replace(',', ''))
                    deaths = int(tags_td[2].text.strip().replace(',', ''))
                except:
                    continue
                if cases != 0:
                    percent = round(deaths / cases * 100, 2)
                total_list.append([region, cases, deaths, percent])
                if region.upper() == 'RUSSIA':
                    printrowfilter(count, region, dataISO, cases, deaths, percent)
                elif count < 10:
                    printrow(count, region, dataISO, cases, deaths, percent)
                count += 1
printfooter()
print(f'count: {len(total_list)}')
cases_min = 1000
print('\nregions with cases > ', cases_min, ':')
# select region where cases > cases_min
list_sort_percent = [i for i in total_list if i[1] > cases_min]

save2json(total_list)
save2csv(total_list)

list_sort_percent = sorted(list_sort_percent, key=lambda item: item[3])
printheader()
count = 0
for row in list_sort_percent:
    region = row[0]
    cases = row[1]
    deaths = row[2]
    percent = row[3]
    if region.upper() == 'RUSSIA':
        printrowfilter(count, region, '', cases, deaths, percent)
    else:
        printrow(count, region, '', cases, deaths, percent)
    count += 1
printfooter()
print(f'count: {len(list_sort_percent)}')
