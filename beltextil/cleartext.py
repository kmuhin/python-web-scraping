#!/usr/bin/env python

# Copyright 2020(c) Konstantin Mukhin Al.

# module
# html parsing
# Make dict with useful data from beltextil url for using later. get_info_from_url()
# Save image from url to file
# String replaces
# Transforming image: resize, crop, align
# Add text over image. stamp_text_over_image()
# Add text at the bottom of image. stamp_text_bottom_image()
# Load settings from ini file
# Save beltextil good information to log file
# Search information in log file. Get code of good, url and etc. stamp_text_bottom_image()

# TODO:
#   Perform log functions as class
#   Make sep func for image transformations
#   Refactor dirty functions
__version__ = '1.18'

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

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
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
PathImage: str = 'pictures'
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
ImageCropSize: tuple = (800, 600)
# read config file
config.read(configname)
PathImage = config.get('DEFAULT', 'PathImage', fallback=PathImage).strip("'").strip('"')
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


def log_url_csv(*args, sep=';'):
    if not args:
        return
    now = f'{datetime.now():%Y-%m-%d %H:%M}'
    with open(urlfilelogname, 'a+', encoding='utf-8') as f:
        f.write(sep.join([now, *args]) + '\n')


def search_in_log_url(text):
    """
        ищет информацию в файле, возвращает список
        дата, артикул, ссылка, артикул простой, имя изображения.
    :param text: text for search
    :return: list of lists
    """

    # remove duplicated spaces
    def text_cooked(string):
        string = string.strip()
        string = re.sub('[",]', ' ', string)
        string = re.sub('см', '', string)
        return re.sub(' +', ' ', string)

    with open(urlfilelogname, 'r', encoding='utf-8') as f:
        logging.debug('search string: ' + text)
        return [line.split(';') for line in f if text_cooked(text) in text_cooked(line)]


def stamp_text_over_image(file_name, message, border=False):
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
    shadow_color = 'yellow'
    if border:
        draw.text((x - 1, y - 1), message, font=font, fill=shadow_color)
        draw.text((x + 1, y - 1), message, font=font, fill=shadow_color)
        draw.text((x, y + 1), message, font=font, fill=shadow_color)
        draw.text((x, y + 1), message, font=font, fill=shadow_color)
    # text
    draw.text((x, y), message, color, font)
    image.save(file_name)


def stamp_text_bottom_image(file_name, message, border=False, resize_size=(), crop=False):
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
        bottom_height = font_size + 20
    else:
        bottom_height = (font_size + 5) * (1 + message.count('\n'))
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
            # Crop делается путем помещения исходного изображения на новое полотно желаемых размеров.
            # Обрезку делаю справа и снизу.
            # Центрирование изображения на полотне.
            # Если размеры полотна больше размеров изображения, добавляются полосы.
            # indentcolor  - цвет полотна и соотвественно полос
            # indentleft - отступ слева
            # indenttop - отступ сверху
            indentcolor = (200, 200, 200)
            indentleft = int((ImageCropSize[0] - image_width) / 2)
            if indentleft < 0:
                indentleft = 0
            indenttop = int((ImageCropSize[1] - image_height) / 2)
            if indenttop < 0:
                indenttop = 0
            # новое полотное с размерами ImageCropSize, цветом indentcolor
            newimage = Image.new('RGB', ImageCropSize, indentcolor)
            logging.debug('indentleft: ' + str(indentleft))
            newimage.paste(image, (indentleft, indenttop))
            image = newimage
            logging.debug('after crop: ' + str(image.size))
            # image.show()
    image_width, image_height = image.size
    # создаю новое полотно image_with_text, на нем рисую текст и вставляю исходное изображение
    image_with_text = Image.new('RGB', (image_width, image_height + bottom_height), (255, 255, 255))
    draw = ImageDraw.Draw(image_with_text)
    # координаты рисования текста
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
    image_with_text.paste(image, (0, 0))
    image_with_text.save(file_name)


def remove_characters(value, chars='\\/:*?"<>|'):
    """
    used to remove invalid chars in filenames
    """
    for ch in chars:
        value = value.replace(ch, '')
    return value


def download_file_rewrite(url, filename='', path='', rewrite=False):
    if not Path(path).is_dir():
        path = ''
    if not filename:
        filename = url.split('/')[-1]
    filename = remove_characters(filename)
    local_filename = os.path.join(path, filename)
    local_filename = str(Path(local_filename).absolute())
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


def get_contents(url, *, headers='', cache=False, cache_dir='', cache_time:int=60):
    contents = ''
    is_overdue = True
    if cache:
        _, filename = url.rsplit("/", 1)
        filename = remove_characters(filename)
        if not cache_dir or Path(cache_dir).is_dir():
            cache_dir = 'Cache'
            Path(cache_dir).mkdir(exist_ok=True)
        file_path = os.path.join(cache_dir, filename)
        now_timestamp: float = datetime.now().timestamp()
        # если в кэше есть, смотрю время изменения st_mtime = timestamp:float.
        # если разница с текущим времене больше cache_time ставлю флаг просрочки is_overdue.
        if Path(file_path).is_file():
            file_mtime = Path(file_path).stat().st_mtime
            is_overdue = now_timestamp - file_mtime > cache_time
    # если без кэша или в кеше просрочка, отправляю запрос
    if not cache or is_overdue:
        try:
            response = requests.get(url, headers=headers)
            contents = response.text
        except requests.exceptions.MissingSchema:
            pass
    # если кэш и не просрочен, считываю из файла
    if cache and not is_overdue:
        with open(file_path, 'r', encoding='utf8') as f:
            contents = f.read()
    # если кэш и просрочено, сохраняю в кэш
    elif cache:
        with open(file_path, 'w', encoding='utf8') as f:
            f.write(contents)
    return contents


def get_info_from_url(url):
    """
    возвращаю data
    data['attrs'] = {}
    data['price'] = {}
    :param url: ссылка
    :return: dict
    """
    #  make schema dictionary
    logging.info('beltextil start:' + str(datetime.now()))
    data = dict.fromkeys(('attrs', 'price'))
    data['attrs'] = {}
    data['price'] = {}
    contents = get_contents(url, headers=headers, cache=True)
    soup = BeautifulSoup(contents, 'html.parser')
    # html - body - div.document - div.main - div.product-view
    # html - body - div.document - div.main - div.product-view - div.pictures - div.front-image - a
    # получаю ссылку на изображение
    image = soup.find('div', attrs={'class': 'front-image'})
    image_url = image.a.attrs['href']
    ## filename = download_file_rewrite(image_url, path=PathImage, rewrite=RewriteDownloadedImage)
    ## logging.debug(filename)
    # Получаю заголовок head
    data['price']['Заголовок'] = re.sub(' +', ' ', soup.html.head.title.text)
    # получаю атрибуты из контейнера <div class=info>
    # html - body - div.document - div.main - div.product-view - div.info
    div_info = soup.find('div', attrs={'class': 'info'})
    div_attributes = div_info.find('div', attrs={'class': 'attributes'})
    # html - body - div.document - div.main - div.product-view - div.div_attributes
    for child in div_attributes:
        if child.name:
            if child.dt.text in DataKeysForPrice:
                data['price'][child.dt.text] = child.dd.text
            else:
                data['attrs'][child.dt.text] = child.dd.text
    # получаю цены и остатки с контейнера <div class=price-helper>
    # кладу в data['price']. Туда же засовываю всю дополнительную инфу.
    # html - body - div.document - div.main - div.product-view - div.info - div.price-helper
    div_pricehelper = div_info.find('div', attrs={'class': 'price-helper'})
    # price.price-helper - table
    number = div_pricehelper.table.contents[0].td.text.strip()
    price = div_pricehelper.table.contents[1].td.div.text.strip()
    # чищу мусор из строк. получаю чистые числа
    number = number.replace('В наличии: ', '').replace(' шт.', '')
    price = price.replace('Цена: ', '').replace(' р.', '').replace(' ', '')
    data['price'] = {**data['price'], 'Цена': price, 'Количество': number, 'Ссылка': url, 'image_url': image_url}

    logging.info('beltextil end:' + str(datetime.now()))
    return data


def complete_processing_url(url: str) -> dict:
    """
    Получение данных по товару.
    Скачивание изображения.
    :param url: str
    :return: dict['attrs', 'price']
    """
    data = get_info_from_url(url)
    filename = download_file_rewrite(data['price']['image_url'], path=PathImage, rewrite=RewriteDownloadedImage)
    logging.debug(filename)
    data['price'] = {**data['price'], 'Картинка': filename}
    # рисую на изображении текст
    # делаю копию изображения
    filenametext = os.path.splitext(filename)[0] + '.text' + os.path.splitext(filename)[1]
    copyfile(filename, filenametext)
    # messagedata - выбираю атрибуты для текста изображения из полученных данных data['attrs'] в нестрогом соответствии.
    messagedata = {'рисунок': '', 'цвет': '', 'состав': '', 'размер': ''}
    for i in data['attrs']:
        # attr = re.split('[ ,]', i.lower())
        for j in messagedata:
            # if j.lower() in attr:
            if j.lower() in i.lower():
                messagedata[j] = data['attrs'][i]
    if messagedata["рисунок"] and messagedata["цвет"]:
        delim = ', '
    else:
        delim = ''
    # message=f'{messagedata["рисунок"]}{delim}{messagedata["цвет"]}\n{messagedata["состав"]}\n{messagedata["размер"]}'
    data['price'] = {**data['price'],
                     'Артикул с текстом': f'{data["price"].get("Артикул", "")} '
                                          f'{messagedata["рисунок"]}{delim}{messagedata["цвет"]}'}
    # text at the image
    if TextOverImage:
        message = Template(TemplateTextOver).substitute(design=messagedata["рисунок"], delim=delim,
                                                        color=messagedata["цвет"], material=messagedata["состав"],
                                                        size=messagedata["размер"])
        stamp_text_over_image(filenametext, message)
    if TextBottomImage:
        message = Template(TemplateTextBottom).substitute(design=messagedata["рисунок"], delim=delim,
                                                          color=messagedata["цвет"], material=messagedata["состав"],
                                                          size=messagedata["размер"])
        stamp_text_bottom_image(filenametext, message, resize_size=ImageResizeSize, crop=ImageCrop)
    data['price'] = {**data['price'], 'Картинка с текстом': filenametext}
    log_url_csv(data['price']['Заголовок'], url, data['price']['Артикул с текстом'], Path(filename).name)
    return data


def info(url):
    data = complete_processing_url(url)
    for i in data:
        print(f'{i:10} {data[i]}')


def main():
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
