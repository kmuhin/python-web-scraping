from bs4 import BeautifulSoup
import requests
import urllib

__version__ = '1.0'

# html navigation
# save picture from url to file
# string replaces

url = 'https://www.beltextil.ru/catalog/1100-kpb-15-sp-valeri'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
}

def remove_characters(value, deletechars):
    for c in deletechars:
        value = value.replace(c,'')
    return value;


def getinfofromurl(url):
    data = {}
    data['attrs'] = {}
    data['price'] = {}
    response = requests.get(url, headers=headers)
    # debug
    with open(f'tmp.html', 'wb') as f:
            f.write(response.content)
    soup = BeautifulSoup(response.text, 'html.parser')

    filename = remove_characters(soup.html.head.title.text, '\/:*?"<>|')+'.jpg'
    # html - body - div.document - div.main - div.product-view
    # html - body - div.document - div.main - div.product-view - div.pictures - div.front-image - a
    picture = soup.find('div', attrs={'class': 'front-image'})
    urllib.request.urlretrieve(picture.a.attrs['href'], filename)
    # html - body - div.document - div.main - div.product-view - div.info
    info = soup.find('div', attrs={'class': 'info'})
    attributes = info.find('div', attrs={'class': 'attributes'})

    # html - body - div.document - div.main - div.product-view - div.attributes
    # вывод атрибутов товара в столбик

    for child in attributes:
        if child.name:
            data['attrs'][child.dt.text] = child.dd.text

    # html - body - div.document - div.main - div.product-view - div.info - div.price-helper
    pricehelper = info.find('div', attrs={'class': 'price-helper'})
    # price.price-helper - table
    number = pricehelper.table.contents[0].td.text.strip()
    price = pricehelper.table.contents[1].td.div.text.strip()
    # чищу мусор из строк. получаю чистые числа
    number = number.replace('В наличии: ', '').replace(' шт.', '')
    price = price.replace('Цена: ', '').replace(' р.', '').replace(' ', '')
    data['price']={'Цена': price, 'Количество': number, 'url': url}
    return data

def info(url):
    data = getinfofromurl(url)
    for i in data:
        print(f'{i:20} {data[i]}')

def main():
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
