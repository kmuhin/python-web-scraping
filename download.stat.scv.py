from datetime import datetime, timedelta
from pathlib import Path
import requests

def download_file(url, workdir='', rewrite=False):
    if workdir:
        workdir += '/'
    local_filename = workdir + url.split('/')[-1]
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


today = datetime.now()
start_date = datetime(2020, 5, 15)
cur_date = start_date
workdir = 'csse_covid_19_daily_reports'
Path(workdir).mkdir(parents=True, exist_ok=True)

while cur_date < today:
    print(cur_date)
    url = f'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/{cur_date:%m-%d-%Y}.csv'
    print(url)
    try:
        download_file(url, workdir)
    except requests.exceptions.HTTPError:
        pass
    cur_date = cur_date + timedelta(days=1)

