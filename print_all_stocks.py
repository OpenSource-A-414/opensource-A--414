'''The MIT License (MIT)

Copyright (c) 2016 Avtandil Kikabidze

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import time
import pykrx # NAVER, KRX(한국거래소)에서 주가정보를 스크래핑하는 오픈소스 라이브러리
from pykrx import stock
from pykrx import bond


def get_code(company_code):
    url="https://finance.naver.com/item/main.nhn?code=" + company_code
    result=requests.get(url)
    bs_obj=BeautifulSoup(result.content, "html.parser")
    return bs_obj

def get_price(company_code):
    bs_obj=get_code(company_code)
    no_today=bs_obj.find("p", {"class":"no_today"})
    blind=no_today.find("span", {"class":"blind"})
    now_price=blind.text
    return now_price

#현재 시간을 구하여 presentTime에 저장
presentTime=time.strftime('%Y%m%d')
print("오늘 날짜", presentTime)

kospi = stock.get_market_ticker_list(presentTime, market="KOSPI")

company_codes = kospi
while True:
    now =datetime.now()
    print(now)

    for item in company_codes:
        now_price=get_price(item)
        print(now_price)
    print("--------------------------")
