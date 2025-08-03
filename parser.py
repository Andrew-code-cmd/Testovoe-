import argparse
import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
from fastapi import FastAPI
import uvicorn

app = FastAPI()

count = 0

def getTenders(page, max_tenders):
    global count
    url = f"https://rostender.info/extsearch?page={page}"

    response = requests.get(url)
    response.raise_for_status()  

    soup = BeautifulSoup(response.text, 'html.parser')

    tenders = []
    for tender in soup.find_all('article', class_='tender-row')[:max_tenders]:
        if count == max_tenders: return tenders
        number = tender.find('span', class_='tender__number').text.split()[-1]
        link = tender.find('a', class_='tender-info__link')['href']
        desc = tender.find('a', class_='description').text.strip()
        otrasl = ' '.join(tender.find('ul', class_='list-branches__ul').text.strip().split())
        place = tender.find('a', class_='tender__region-link').text.strip()  
        start_date = tender.find('span', class_='tender__date-start').text.strip() 
        end_date = tender.find('span', class_='tender__countdown-text').text.strip()  
        
        tenders.append({
            'number': number,
            'link': link,
            'desc': desc,
            'otrasl': otrasl,
            'place': place,
            'start_date': start_date,
            'end_date': end_date
        })

        count += 1

    return tenders

def saveSqlLite(tenders):
    conn = sqlite3.connect('tenders.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY,
            number TEXT,
            link TEXT,
            desc TEXT,
            otrasl TEXT,
            place TEXT,
            start_date TEXT,
            end_date TEXT
        );
    ''')
    
    for tender in tenders:
        cursor.execute('''
            INSERT INTO tenders (number, link, otrasl, desc, place, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (tender['number'], tender['link'], tender['otrasl'], tender['desc'],
                                              tender['place'], tender['start_date'], tender['end_date']))
    
    conn.commit()
    conn.close()

def saveExcel(tenders):
    df = pd.DataFrame(tenders)
    out = "tenders.xlsx"
    df.to_excel(out, index=False, sheet_name="Тендеры")

def main(max_tenders, output):
    all_tenders = []
    page = 1

    while True:
        if page == 3: break

        tenders = getTenders(page, max_tenders)
        if not tenders:
            break
        all_tenders.extend(tenders)
        print(f'Получено {len(tenders)} тендеров с страницы {page}')
        page += 1
    
    print(f'Всего найдено тендеров: {len(all_tenders)}')


    if(output == "tenders.xlsx"):
        saveExcel(all_tenders)
    else: saveSqlLite(all_tenders)

    
@app.get("/tenders")
def get_tenders():
    conn = sqlite3.connect('tenders.db')
    df = pd.read_sql_query("SELECT * FROM tenders", conn)
    conn.close()
    return df.to_dict(orient="records")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=10)
    parser.add_argument('--output', type=str, default='tenders.db')
    
    args = parser.parse_args()
    
    main(args.max, args.output)
    uvicorn.run(app, host="127.0.0.1", port=8000)
