#!/usr/bin/env python


from bs4 import BeautifulSoup
import configparser
from pathlib import Path
import requests
import urllib
import os
import logging, sys


__version__ = '1.3'

# module
# html navigation
# save picture from url to file
# string replaces

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
}

workdir = Path(__file__).parent.absolute()
workfile = Path(__file__).absolute()

config = configparser.ConfigParser()
#configname = str(workdir) + '\\' + workfile.stem + '.ini'
configname = os.path.join(str(workdir), workfile.stem + '.ini')
logging.debug('ini file:', configname)
config.read(configname)
DataKeysForPrice = ['Артикул']

pathpictures = str(workdir)
rewritepicture = False
try:
    pathpictures = config['DEFAULT']['pathpictures'].strip("'").strip('"')
    rewritepicture = config['DEFAULT'].getboolean('rewritepictures')
except KeyError:
    pass


def remove_characters(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '')
    return value;



def download_file_rewrite(url, filename='', path='', rewrite=False):
    if not Path(path).is_dir():
        path = ''
    if not filename:
        filename = url.split('/')[-1]
    local_filename = os.path.join(path,filename)
    if Path(local_filename).is_file() and not rewrite:
        return local_filename
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush()
    return local_filename


def getinfofromurl(url):
    #  make schema dictionary
    data = dict.fromkeys(('attrs', 'price'))
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.MissingSchema:
        return data
    data['attrs'] = {}
    data['price'] = {}
    # debug save html
    with open(f'tmp.html', 'wb') as f:
        f.write(response.content)
    #
    soup = BeautifulSoup(response.text, 'html.parser')
    filename = remove_characters(soup.html.head.title.text, '\/:*?"<>|') + '.jpg'
    # html - body - div.document - div.main - div.product-view
    # html - body - div.document - div.main - div.product-view - div.pictures - div.front-image - a
    picture = soup.find('div', attrs={'class': 'front-image'})
    picture_url = picture.a.attrs['href']
    # urllib.request.urlretrieve(picture_url, pathpictures+filename)
    filename = download_file_rewrite(picture_url, path=pathpictures, rewrite=rewritepicture)
    # html - body - div.document - div.main - div.product-view - div.info
    info = soup.find('div', attrs={'class': 'info'})
    attributes = info.find('div', attrs={'class': 'attributes'})

    # html - body - div.document - div.main - div.product-view - div.attributes
    for child in attributes:
        if child.name:
            if child.dt.text in DataKeysForPrice:
                data['price'][child.dt.text] = child.dd.text
            else:
                data['attrs'][child.dt.text] = child.dd.text

    # html - body - div.document - div.main - div.product-view - div.info - div.price-helper
    pricehelper = info.find('div', attrs={'class': 'price-helper'})
    # price.price-helper - table
    number = pricehelper.table.contents[0].td.text.strip()
    price = pricehelper.table.contents[1].td.div.text.strip()
    # чищу мусор из строк. получаю чистые числа
    number = number.replace('В наличии: ', '').replace(' шт.', '')
    price = price.replace('Цена: ', '').replace(' р.', '').replace(' ', '')
    data['price'] = {**data['price'], 'Цена': price, 'Количество': number, 'Картинка': filename, 'Ссылка': url}
    return data


def info(url):
    data = getinfofromurl(url)
    for i in data:
        print(f'{i:20} {data[i]}')


def main() -> object:
    info('https://www.beltextil.ru/catalog/14s80-shr-v-up-215148-kpb-kvartet-ris-7-cv-12-korall')
    while True:
        try:
            url = input('type url or exit: ')
            if url.upper() in ['EXIT', 'QUIT']:
                break
            info(url)
            print()
        except requests.exceptions.MissingSchema:
            print('Invalid URL. Try again.')


if __name__ == '__main__':
    main()
