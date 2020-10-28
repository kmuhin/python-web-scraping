#!/usr/bin/env python

# Copyright (c) 2020 Konstantin Mukhin Al.

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

__version__ = '1.22'

import configparser
from functools import wraps
import logging
import os
import re
import sys
from datetime import datetime
import time

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
enable_wrap_timing = True
logging.info('workdir: ' + str(workdir))
logging.info('workfile: ' + str(workfile))

config_parser = configparser.ConfigParser()
configname = os.path.join(str(workdir), workfile.stem + '.ini')
urlfilelogname = os.path.join(str(workdir), workfile.stem + '.log')
logging.debug('ini file:' + configname)

# filter to move values from data['attrs'] to data['price']
DataKeysForPrice = ['Артикул']

# set default values before read config
path_image: str = 'pictures'
bln_rewrite_downloaded_image: bool = False
bln_textoverimage: bool = False
bln_textbottomimage: bool = True
template_text_bottom: str = '$design$delim$color'
template_text_over: str = '$design\n$color'
color_text_bottom: str = 'black'
color_text_over: str = 'white'
font_size_bottom: int = 45
font_size_over: int = 45
bln_imageresize: bool = False
image_resize_size = (800, 600)
bln_imagecrop: bool = False
image_crop_size: tuple = (800, 600)

# read config file
config_parser.read(configname)
path_image = config_parser.get('DEFAULT', 'PathImage', fallback=path_image).strip('\'"')
bln_rewrite_downloaded_image = config_parser.getboolean('DEFAULT', 'RewriteDownloadedImage',
                                                        fallback=bln_rewrite_downloaded_image)
bln_textoverimage = config_parser.getboolean('DEFAULT', 'textoverimage', fallback=bln_textoverimage)
bln_textbottomimage = config_parser.getboolean('DEFAULT', 'textbottomimage', fallback=bln_textbottomimage)
template_text_bottom = config_parser.get('DEFAULT', 'templatetextbottom', fallback=template_text_bottom)
template_text_over = config_parser.get('DEFAULT', 'templatetextover', fallback=template_text_over)
color_text_bottom = config_parser.get('DEFAULT', 'colortextbottom', fallback=color_text_bottom)
color_text_over = config_parser.get('DEFAULT', 'colortextover', fallback=color_text_over)
font_size_bottom = int(config_parser.get('DEFAULT', 'fontsizebottom', fallback=font_size_bottom))
font_size_over = int(config_parser.get('DEFAULT', 'fontsizeover', fallback=font_size_over))
bln_imageresize = config_parser.getboolean('IMAGETRANSFORM', 'imageresize', fallback=bln_imageresize)
bln_imagecrop = config_parser.getboolean('IMAGETRANSFORM', 'imagecrop', fallback=bln_imagecrop)
if config_parser.get('IMAGETRANSFORM', 'imagecropsize', fallback=None):
    image_crop_size = config_parser.get('IMAGETRANSFORM', 'imagecropsize')
    image_crop_size = tuple(map(int, image_crop_size.split(',')))
if config_parser.get('IMAGETRANSFORM', 'imageresizesize', fallback=None):
    image_resize_size = config_parser.get('IMAGETRANSFORM', 'imageresizesize')
    image_resize_size = tuple(map(int, image_resize_size.split(',')))

logging.debug('template string: ' + template_text_bottom)


def wrap_timing(f):
    if not enable_wrap_timing:
        return f

    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time.perf_counter()
        result = f(*args, **kwargs)
        te = time.perf_counter()
        logging.info(f'func:{f.__name__[:20]:20}  took: {te - ts}')
        return result

    return wrap


class ImageSimple(object):
    def __init__(self, file_name):
        """

        :param file_name: image file name
        """
        self.image = Image.open(file_name)
        self.file_name = file_name
        self.font_name = os.path.join(str(workdir), 'FreeSans.ttf')

    def save(self, file_name: str = None):
        """
        saving changes to file with file_name if specified
        or to original file name
        :type file_name: str
        :return: None
        """
        file_name = file_name or self.file_name
        self.image.save(file_name)

    def resize(self, resize_size=()):
        """
        resize image
        """
        logging.debug('before resize: ' + str(self.image.size))
        resize = resize_size
        logging.debug('desired size: ' + str(resize))
        self.image.thumbnail(resize, Image.ANTIALIAS)
        logging.debug('after resize: ' + str(self.image.size))

    def crop(self, crop_size=()):
        """
        # Crop делается путем помещения исходного изображения на новое полотно желаемых размеров.
        # Обрезку делаю справа и снизу.
        # Центрирование изображения на полотне.
        # Если размеры полотна больше размеров изображения, добавляются полосы.
        # indentcolor  - цвет полотна и соотвественно полос
        # indentleft - отступ слева
        # indenttop - отступ сверху
        """
        bgcolor = (200, 200, 200)
        image_width, image_height = self.image.size
        logging.debug('before crop: ' + str(self.image.size))
        indentleft = int((crop_size[0] - image_width) / 2)
        if indentleft < 0:
            indentleft = 0
        indenttop = int((crop_size[1] - image_height) / 2)
        if indenttop < 0:
            indenttop = 0
        # новое полотное с размерами ImageCropSize, цветом indentcolor
        newimage = Image.new('RGB', crop_size, bgcolor)
        logging.debug('indentleft: ' + str(indentleft))
        newimage.paste(self.image, (indentleft, indenttop))
        self.image = newimage
        logging.debug('after crop: ' + str(self.image.size))

    def text_over_image(self, message, font_size=42, border=False,
                        color='black', shadow_color='yellow'):
        """
        the function draws text over the image from file

        :param shadow_color:
        :param color:
        :param font_size: font size
        :type message: str
        :type border: bool
        :param border: draw border around text
        :param message: text for drawing
        """
        draw = ImageDraw.Draw(self.image)
        font = ImageFont.truetype(self.font_name, size=font_size)
        (x, y) = (10, 10)
        # border
        if border:
            draw.text((x - 1, y - 1), message, font=font, fill=shadow_color)
            draw.text((x + 1, y - 1), message, font=font, fill=shadow_color)
            draw.text((x, y + 1), message, font=font, fill=shadow_color)
            draw.text((x, y + 1), message, font=font, fill=shadow_color)
        # text
        draw.text((x, y), message, color, font)

    def text_bottom_image(self, message, font_size=42, border=False,
                          color='black', shadow_color='yellow'):
        """
        the function draws text below the image from file

        :param shadow_color:
        :param color:
        :param font_size: font size
        :param border: border around text
        :param message: text for drawing
        """
        if message.count('\n') == 0:
            bottom_height = font_size + 20
        else:
            bottom_height = (font_size + 5) * (1 + message.count('\n'))
        font = ImageFont.truetype(self.font_name, size=font_size)
        image_width, image_height = self.image.size
        # создаю новое полотно image_with_text, на нем рисую текст и вставляю исходное изображение
        image_with_text = Image.new('RGB', (image_width, image_height + bottom_height), (255, 255, 255))
        draw = ImageDraw.Draw(image_with_text)
        # координаты рисования текста
        (x, y) = (10, image_height + 10)
        # text outline
        if border:
            draw.text((x - 1, y - 1), message, font=font, fill=shadow_color)
            draw.text((x + 1, y - 1), message, font=font, fill=shadow_color)
            draw.text((x, y + 1), message, font=font, fill=shadow_color)
            draw.text((x, y + 1), message, font=font, fill=shadow_color)
        # text
        draw.text((x, y), message, color, font)
        # add existed image to new
        image_with_text.paste(self.image, (0, 0))
        self.image = image_with_text


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

    def text_cooked(string):
        string = re.sub('[",]', ' ', string)
        string = re.sub('см', '', string)
        # remove duplicated spaces
        string = ' '.join(string.split())
        return string

    with open(urlfilelogname, 'r', encoding='utf-8') as f:
        logging.debug('search string: ' + text)
        return [line.split(';') for line in f if text_cooked(text) in text_cooked(line)]


def remove_characters(value, chars='\\/:*?"<>|'):
    """
    used to remove invalid chars in filenames
    """
    for ch in chars:
        value = value.replace(ch, '')
    return value


def download_file_rewrite(url, filename='', path='', rewrite=False):
    if not Path(path).is_dir():
        logging.error('download path does not exist: ' + path)
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


def get_contents(url, *, headers='', cache=False, cache_dir='', cache_time: int = 300):
    """
        takes url and return str with html

    input:
     url: url http://www.site.ru/...
     header: http headers (agent, cookies, ...)
     cache: whether to use the cache
     cache_dir: directory of cache
     cache_time: life time of cache
    output:
     content: html as text
    """
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
    data = dict.fromkeys(('attrs', 'price'))
    data['attrs'] = {}
    data['price'] = {}
    contents = get_contents(url, headers=headers, cache=True, cache_time=600)
    # soup = BeautifulSoup(contents, 'html.parser')
    soup = BeautifulSoup(contents, 'html.parser')
    # html - body - div.document - div.main - div.product-view
    # html - body - div.document - div.main - div.product-view - div.pictures - div.front-image - a
    # получаю ссылку на изображение
    image = soup.find('div', attrs={'class': 'front-image'})
    image_url = image.a.attrs['href']
    # Получаю заголовок head. Удаляю пробелы больше 1 подряд.
    # По моим тестам через split работает быстрее чем через re.sub
    # data['price']['Заголовок'] = re.sub(' +', ' ', soup.html.head.title.text)
    data['price']['Заголовок'] = ' '.join(soup.html.head.title.text.split())
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
    data['price'].update({'Цена': price, 'Количество': number, 'Ссылка': url, 'image_url': image_url})

    return data


def complete_processing_url(url: str) -> dict:
    """
    Получение данных по товару.
    Скачивание изображения.
    :param url: str
    :return: dict['attrs', 'price']
    """
    data = get_info_from_url(url)
    filename = download_file_rewrite(data['price']['image_url'], path=path_image, rewrite=bln_rewrite_downloaded_image)
    data['price']['Картинка'] = filename
    # рисую на изображении текст
    # делаю копию изображения
    filenametext = os.path.splitext(filename)[0] + '.text' + os.path.splitext(filename)[1]
    copyfile(filename, filenametext)
    # messagedata - выбираю атрибуты для текста изображения из полученных данных data['attrs'] в нестрогом соответствии.
    messagedata = {'рисунок': '', 'цвет': '', 'состав': '', 'размер': ''}
    for i in data['attrs']:
        for j in messagedata:
            if j.lower() in i.lower():
                messagedata[j] = data['attrs'][i]
    if messagedata["рисунок"] and messagedata["цвет"]:
        delim = ', '
    else:
        delim = ''
    data['price']['Артикул с текстом'] = (f'{data["price"].get("Артикул", "")} '
                                          f'{messagedata["рисунок"]}{delim}{messagedata["цвет"]}')
    # text at the image
    image = ImageSimple(filenametext)
    if bln_imageresize:
        image.resize(resize_size=image_resize_size)
    if bln_imagecrop:
        image.crop(crop_size=image_crop_size)
    if bln_textoverimage:
        message = Template(template_text_over).substitute(design=messagedata["рисунок"], delim=delim,
                                                          color=messagedata["цвет"], material=messagedata["состав"],
                                                          size=messagedata["размер"])
        image.text_over_image(message, font_size=font_size_over, color=color_text_over)
    if bln_textbottomimage:
        message = Template(template_text_bottom).substitute(design=messagedata["рисунок"], delim=delim,
                                                            color=messagedata["цвет"], material=messagedata["состав"],
                                                            size=messagedata["размер"])
        image.text_bottom_image(message, font_size=font_size_bottom, color=color_text_bottom)
    image.save()
    data['price']['Картинка с текстом'] = filenametext
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
