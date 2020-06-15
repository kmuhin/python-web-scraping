#!/usr/bin/env python


from bs4 import BeautifulSoup
import configparser
from pathlib import Path
import requests
import re
import os
from shutil import copyfile
import logging, sys
from PIL import Image, ImageDraw, ImageFont


__version__ = '1.6'

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
#configname = str(workdir) + '\\' + workfile.stem + '.ini'
configname = os.path.join(str(workdir), workfile.stem + '.ini')
logging.debug('ini file:' + configname)
config.read(configname)
DataKeysForPrice = ['Артикул']

pathpictures = str(workdir)
rewritepicture = False
try:
    pathpictures = config['DEFAULT']['pathpictures'].strip("'").strip('"')
    rewritepicture = config['DEFAULT'].getboolean('rewritepictures')
except KeyError:
    pass

def imagestamp(filename, message, border=False):
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(str(workdir),'FreeSans.ttf'), size=45)

    (x, y) = (10, 10)
# border
    color = 'black'
    shadowcolor = 'yellow'
    if border:
      draw.text((x-1, y-1), message, font=font, fill=shadowcolor)
      draw.text((x+1, y-1), message, font=font, fill=shadowcolor)
      draw.text((x, y+1), message, font=font, fill=shadowcolor)
      draw.text((x, y+1), message, font=font, fill=shadowcolor)
# text
    draw.text((x, y), message, color, font)
    image.save(filename)

def imagestampextend(filename, message, border=False, resizesize=(), crop=False):
    image = Image.open(filename)
    font = ImageFont.truetype(os.path.join(str(workdir),'FreeSans.ttf'), size=45)
    imagewidth, imageheight = image.size
# resize image
    if resizesize:
      logging.debug('before resize: ' + str(image.size))
#      if imagewidth/resizesize(0) >= imageheight/resizesize(2):
#          resize = (resizesize(0),imageheight)
#      else:
#          resize = (imagewidth,resizesize(1))
#    resize = (resizesize(0),imageheight)
      resize = resizesize
      logging.debug('desired size: ' + str(resize))
      image.thumbnail(resize, Image.ANTIALIAS)
      logging.debug('after resize, before crop: ' + str(image.size))
      imagewidth, imageheight = image.size
# crop image
      if crop:
          indentwidth = int((resizesize[0]-imagewidth)/2)
          if indentwidth < 0:
              indentiwdth = 0
          indentheight = int((resizesize[1]-imageheight)/2)
          if indentwidth < 0:
              indentiwdth = 0
          if indentwidth < 0:
              indentheight = 0
          newimage = Image.new('RGB', resizesize, (200,200,200))
          logging.debug('indentwidth: ' + str(indentwidth))
          newimage.paste(image, (indentwidth, indentheight))
          image = newimage
          logging.debug('after crop: ' + str(image.size))
#          image.show()
      imagewidth, imageheight = image.size
# new image
#    logging.debug('after crop: ' + str(image.size))
#    background = Image.new('RGB', (imagewidth, imageheight+150), (255,255,255))
    imagewidth, imageheight = image.size
    background = Image.new('RGB', (imagewidth, imageheight+150), (255,255,255))
    draw = ImageDraw.Draw(background)
    (x, y) = (10, imageheight+10)
    color = 'black'
    shadowcolor = 'yellow'
# text outline
    if border:
      draw.text((x-1, y-1), message, font=font, fill=shadowcolor)
      draw.text((x+1, y-1), message, font=font, fill=shadowcolor)
      draw.text((x, y+1), message, font=font, fill=shadowcolor)
      draw.text((x, y+1), message, font=font, fill=shadowcolor)
# text
    draw.text((x, y), message, color, font)
# add existed image to new
    background.paste(image, (0, 0))
    background.save(filename)


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
    filename = download_file_rewrite(picture_url, path=pathpictures, rewrite=rewritepicture)
    logging.debug(filename)
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
    # рисую на изображении текст
    # делаю копию изображения
    filenametext = os.path.splitext(filename)[0]+'.text'+ os.path.splitext(filename)[1]
    copyfile(filename,filenametext)
    # заданные атрибуты для текста ищу в полученных данных в нестрогом соответсвии.
    messagedata = {'рисунок' : '', 'цвет': '', 'состав': '', 'размер': ''}
    for i in data['attrs']:
      attr = re.split('[ ,]',i.lower())
      for j in messagedata:
          if j.lower() in attr:
              messagedata[j] = data['attrs'][i]
    message=f'{messagedata["рисунок"]}, {messagedata["цвет"]}\n{messagedata["состав"]}\n{messagedata["размер"]}'
#  imagestamp(filenametext, data['attrs']['Рисунок']+'\n'+data['attrs']['Цвет'])
# text at the image
    if message:
        imagestampextend(filenametext, message, resizesize=(800, 600), crop=True)
    data['price'] = {**data['price'], 'Картинка с текстом' : filenametext}
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
