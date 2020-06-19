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

__version__ = '1.8'

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
PathImage: str = str(workdir)
RewriteDownloadedImage: bool = False
TextOverImage: bool = False
TextBottomImage: bool = True
TemplateTextBottom: str = '$design$delim$color'
TemplateTextOver: str = '$design\n$color'
ColorTextBottom: str = 'black'
ColorTextOver: str = 'white'
FontSizeBottom: int = 45
FontSizeOver: int = 45
ImageResize: bool = False
ImageResizeSize = (800, 600)
ImageCrop: bool = False
ImageCropSize = (800, 600)
# read config file
config.read(configname)
PathImage = config.get('DEFAULT', 'pathImage', fallback=PathImage).strip("'").strip('"')
RewriteDownloadedImage = config.getboolean('DEFAULT', 'RewriteDownloadedImage', fallback=RewriteDownloadedImage)
TextOverImage = config.getboolean('DEFAULT', 'textoverimage', fallback=TextOverImage)
TextBottomImage = config.getboolean('DEFAULT', 'textbottomimage', fallback=TextBottomImage)
TemplateTextBottom = config.get('DEFAULT', 'templatetextbottom', fallback=TemplateTextBottom)
TemplateTextOver = config.get('DEFAULT', 'templatetextover', fallback=TemplateTextOver)
ColorTextBottom = config.get('DEFAULT', 'colortextbottom', fallback=ColorTextBottom)
ColorTextOver = config.get('DEFAULT', 'colortextover', fallback=ColorTextOver)
FontSizeBottom = int(config.get('DEFAULT', 'fontsizebottom', fallback=FontSizeBottom))
FontSizeOver = int(config.get('DEFAULT', 'fontsizeover', fallback=FontSizeOver))
ImageResize = config.getboolean('IMAGETRANSFORM', 'imageresize', fallback=ImageResize)
ImageCrop = config.getboolean('IMAGETRANSFORM', 'imagecrop', fallback=ImageCrop)
if config.get('IMAGETRANSFORM', 'imagecropsize', fallback=None):
    ImageCropSize = config.get('IMAGETRANSFORM', 'imagecropsize')
    ImageCropSize = tuple(map(int, ImageCropSize.split(',')))
if config.get('IMAGETRANSFORM', 'imageresizesize', fallback=None):
    ImageResizeSize = config.get('IMAGETRANSFORM', 'imageresizesize')
    ImageResizeSize = tuple(map(int, ImageResizeSize.split(',')))


logging.debug('template string: ' + TemplateTextBottom)


def LogUrl(title, url):
    now = datetime.now()
    with open(urlfilelogname, 'a+', encoding='utf-8') as f:
        f.write(f'{now:%Y-%m-%d %H:%M};{title};{url}\n')


def StampTextOverImage(file_name, message, border=False):
    """
    the function draws text over the image from file

    :type message: str
    :type border: bool
    :param border: draw border around text
    :param message: text for drawing
    :type file_name: str
    :param file_name: name of file of image
    """
    image = Image.open(file_name)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(str(workdir), 'FreeSans.ttf'), size=FontSizeOver)

    (x, y) = (10, 10)
    # border
    color = ColorTextOver
    shadowcolor = 'yellow'
    if border:
        draw.text((x - 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x + 1, y - 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
        draw.text((x, y + 1), message, font=font, fill=shadowcolor)
    # text
    draw.text((x, y), message, color, font)
    image.save(file_name)


def StampTextBottomImage(file_name, message, border=False, resize_size=(), crop=False):
    """
    the function draws text below the image from file

    :param file_name: name of file of image
    :param crop: crop image
    :param border: border around text
    :param message: text for drawing
    :type resize_size: tuple
    """
    image = Image.open(file_name)
    font_size = FontSizeBottom
    font = ImageFont.truetype(os.path.join(str(workdir), 'FreeSans.ttf'), size=font_size)
    if message.count('\n') == 0:
        bottomhight = font_size + 20
    else:
        bottomhight = (font_size + 5) * (1 + message.count('\n'))
    image_width, image_height = image.size
    # resize image
    if ImageResize:
        logging.debug('before resize: ' + str(image.size))
        resize = resize_size
        logging.debug('desired size: ' + str(resize))
        image.thumbnail(resize, Image.ANTIALIAS)
        logging.debug('after resize, before crop: ' + str(image.size))
        image_width, image_height = image.size
        # crop image
        if crop:
            indentwidth = int((ImageCropSize[0] - image_width) / 2)
            if indentwidth < 0:
                indentwidth = 0
            indentheight = int((ImageCropSize[1] - image_height) / 2)
            if indentheight < 0:
                indentheight = 0
            newimage = Image.new('RGB', ImageCropSize, (200, 200, 200))
            logging.debug('indentwidth: ' + str(indentwidth))
            newimage.paste(image, (indentwidth, indentheight))
            image = newimage
            logging.debug('after crop: ' + str(image.size))
        #          image.show()
    image_width, image_height = image.size
    background = Image.new('RGB', (image_width, image_height + bottomhight), (255, 255, 255))
    draw = ImageDraw.Draw(background)
    (x, y) = (10, image_height + 10)
    color = ColorTextBottom
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
    background.save(file_name)


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


def GetInfoFromUrl(url: str) -> dict:
    """

    :param url: str
    :return: dict['attrs', 'price']
    """
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
    image = soup.find('div', attrs={'class': 'front-image'})
    image_url = image.a.attrs['href']
    filename = download_file_rewrite(image_url, path=PathImage, rewrite=RewriteDownloadedImage)
    logging.debug(filename)
    # html - body - div.document - div.main - div.product-view - div.info
    div_info = soup.find('div', attrs={'class': 'info'})
    data['price']['Заголовок'] = soup.html.head.title.text
    LogUrl(data['price']['Заголовок'], url)
    attributes = div_info.find('div', attrs={'class': 'attributes'})

    # html - body - div.document - div.main - div.product-view - div.attributes
    for child in attributes:
        if child.name:
            if child.dt.text in DataKeysForPrice:
                data['price'][child.dt.text] = child.dd.text
            else:
                data['attrs'][child.dt.text] = child.dd.text

    # html - body - div.document - div.main - div.product-view - div.info - div.price-helper
    div_pricehelper = div_info.find('div', attrs={'class': 'price-helper'})
    # price.price-helper - table
    number = div_pricehelper.table.contents[0].td.text.strip()
    price = div_pricehelper.table.contents[1].td.div.text.strip()
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
                     'Артикул с текстом': f'{data["price"].get("Артикул","")} '
                     f'{messagedata["рисунок"]}{delim}{messagedata["цвет"]}'}
    # text at the image
    if TextOverImage:
        message = Template(TemplateTextOver).substitute(design=messagedata["рисунок"], delim=delim,
                                                        color=messagedata["цвет"], material=messagedata["состав"],
                                                        size=messagedata["размер"])
        StampTextOverImage(filenametext, message)
    if TextBottomImage:
        message = Template(TemplateTextBottom).substitute(design=messagedata["рисунок"], delim=delim,
                                                          color=messagedata["цвет"], material=messagedata["состав"],
                                                          size=messagedata["размер"])
        StampTextBottomImage(filenametext, message, resize_size=ImageResizeSize, crop=ImageCrop)
    data['price'] = {**data['price'], 'Картинка с текстом': filenametext}
    return data


def info(url):
    data = GetInfoFromUrl(url)
    for i in data:
        print(f'{i:10} {data[i]}')


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
