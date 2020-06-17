#!/usr/bin/env python


import configparser
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from string import Template

import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

__version__ = '1.7'

# module
# html navigation
# save picture from url to file
# string replaces
# transforming image: resize, crop, align.
# add text over image
# add text at the bottom of image


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
}

workdir = Path(__file__).parent.absolute()
workfile = Path(__file__).absolute()

config = configparser.ConfigParser()
# configname = str(workdir) + '\\' + workfile.stem + '.ini'
configname = os.path.join(str(workdir), workfile.stem + '.ini')
urlfilelogname = os.path.join(str(workdir), workfile.stem + '.log')
logging.debug('ini file:' + configname)

# filter to move values from data['attrs'] to data['price']
DataKeysForPrice = ['Артикул']

# set default values before read config
pathpictures = str(workdir)
rewritepicture = False
textoverimage = False
textbottomimage = True
templatetextbottom = '$design$delim$color'
templatetextover = '$design\n$color'
colortextbottom = 'black'
colortextover = 'white'
fontsizebottom = 45
fontsizeover = 45
imageresize = False
imageresizesize = (800, 600)
imagecrop = False
imagecropsize = (800, 600)
# read config file
try:
    config.read(configname)
    pathpictures = config['DEFAULT']['pathpictures'].strip("'").strip('"')
    rewritepicture = config['DEFAULT'].getboolean('rewritepictures')
    textoverimage = config['DEFAULT'].getboolean('textoverimage')
    textbottomimage = config['DEFAULT'].getboolean('textbottomimage')
    templatetextbottom = config['DEFAULT']['templatetextbottom']
    templatetextover = config['DEFAULT']['templatetextover']
    colortextbottom = config['DEFAULT']['colortextbottom']
    colortextover = config['DEFAULT']['colortextover']
    fontsizebottom = int(config['DEFAULT']['fontsizebottom'])
    fontsizeover = int(config['DEFAULT']['fontsizeover'])

    imageresize = config['IMAGETRANSFORM'].getboolean('imageresize')
    imagecrop = config['IMAGETRANSFORM'].getboolean('imagecrop')
    imagecropsize = config['IMAGETRANSFORM']['imagecropsize']
    imagecropsize = tuple(map(int, imagecropsize.split(',')))
    imageresizesize = config['IMAGETRANSFORM']['imageresizesize']
    imageresizesize = tuple(map(int, imageresizesize.split(',')))
except KeyError:
    pass

logging.debug('template string: ' + templatetextbottom)


def logurl(title, url):
    now = datetime.now()
    with open(urlfilelogname, 'a+') as f:
        f.write(f'{now:%Y-%m-%d %H:%M};{title};{url}\n')


def imagestamp(filename, message, border=False):
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(str(workdir), 'FreeSans.ttf'), size=fontsizeover)

    (x, y) = (10, 10)
    # border
    color = colortextover
    shadowcolor = 'yellow'
    if border:
        draw.text((x - 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x + 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
    # text
    draw.text((x, y), message, color, font)
    image.save(filename)


def imagestampextend(filename, message, border=False, resizesize=(), crop=False):
    image = Image.open(filename)
    fontsize = fontsizebottom
    font = ImageFont.truetype(os.path.join(str(workdir), 'FreeSans.ttf'), size=fontsize)
    if message.count('\n') == 0:
        bottomhight = fontsize + 20
    else:
        bottomhight = (fontsize + 5) * (1 + message.count('\n'))
    imagewidth, imageheight = image.size
    # resize image
    if imageresize:
        logging.debug('before resize: ' + str(image.size))
        resize = resizesize
        logging.debug('desired size: ' + str(resize))
        image.thumbnail(resize, Image.ANTIALIAS)
        logging.debug('after resize, before crop: ' + str(image.size))
        imagewidth, imageheight = image.size
        # crop image
        if crop:
            indentwidth = int((imagecropsize[0] - imagewidth) / 2)
            if indentwidth < 0:
                indentwidth = 0
            indentheight = int((imagecropsize[1] - imageheight) / 2)
            if indentheight < 0:
                indentheight = 0
            newimage = Image.new('RGB', imagecropsize, (200, 200, 200))
            logging.debug('indentwidth: ' + str(indentwidth))
            newimage.paste(image, (indentwidth, indentheight))
            image = newimage
            logging.debug('after crop: ' + str(image.size))
        #          image.show()
    imagewidth, imageheight = image.size
    background = Image.new('RGB', (imagewidth, imageheight + bottomhight), (255, 255, 255))
    draw = ImageDraw.Draw(background)
    (x, y) = (10, imageheight + 10)
    color = colortextbottom
    shadowcolor = 'yellow'
    # text outline
    if border:
        draw.text((x - 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x + 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
    # text
    draw.text((x, y), message, color, font)
    # add existed image to new
    background.paste(image, (0, 0))
    background.save(filename)


def remove_characters(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '')
    return value


def download_file_rewrite(url, filename='', path='', rewrite=False):
    if not Path(path).is_dir():
        path = ''
    if not filename:
        filename = url.split('/')[-1]
    local_filename = os.path.join(path, filename)
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
    filename = download_file_rewrite(picture_url, path=pathpictures, rewrite=rewritepicture)
    logging.debug(filename)
    # html - body - div.document - div.main - div.product-view - div.info
    info = soup.find('div', attrs={'class': 'info'})
    data['price']['Заголовок'] = soup.html.head.title.text
    logurl(data['price']['Заголовок'], url)
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
    # рисую на изображении текст
    # делаю копию изображения
    filenametext = os.path.splitext(filename)[0] + '.text' + os.path.splitext(filename)[1]
    copyfile(filename, filenametext)
    # заданные атрибуты для текста ищу в полученных данных в нестрогом соответсвии.
    messagedata = {'рисунок': '', 'цвет': '', 'состав': '', 'размер': ''}
    for i in data['attrs']:
        attr = re.split('[ ,]', i.lower())
        for j in messagedata:
            if j.lower() in attr:
                messagedata[j] = data['attrs'][i]
    if messagedata["рисунок"] and messagedata["цвет"]:
        delim = ', '
    else:
        delim = ''
    # message=f'{messagedata["рисунок"]}{delim}{messagedata["цвет"]}\n{messagedata["состав"]}\n{messagedata["размер"]}'
    data['price'] = {**data['price'],
                     'Артикул с текстом': f'{data["price"]["Артикул"]} {messagedata["рисунок"]}{delim}{messagedata["цвет"]}'}
    # text at the image
    if textoverimage:
        message = Template(templatetextover).substitute(design=messagedata["рисунок"], delim=delim,
                                                        color=messagedata["цвет"], material=messagedata["состав"],
                                                        size=messagedata["размер"])
        imagestamp(filenametext, message)
    if textbottomimage:
        message = Template(templatetextbottom).substitute(design=messagedata["рисунок"], delim=delim,
                                                          color=messagedata["цвет"], material=messagedata["состав"],
                                                          size=messagedata["размер"])
        imagestampextend(filenametext, message, resizesize=imageresizesize, crop=imagecrop)
    data['price'] = {**data['price'], 'Картинка с текстом': filenametext}
    return data


def info(url):
    data = getinfofromurl(url)
    for i in data:
        print(f'{i:20} {data[i]}')


def main() -> object:
    info('https://www.beltextil.ru/catalog/14s80-shr-v-up-215148-kpb-kvartet-ris-7-cv-12-korall')

'''    while True:
        try:
            url = input('type url or exit: ')
            if url.upper() in ['EXIT', 'QUIT']:
                break
            info(url)
            print()
        except requests.exceptions.MissingSchema:
            print('Invalid URL. Try again.')
'''

if __name__ == '__main__':
    main()
