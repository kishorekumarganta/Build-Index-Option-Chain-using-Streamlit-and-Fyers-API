import streamlit as st
import pandas as pd
import  time

import numpy as np
import requests
import urllib.parse as urlparse
from urllib.parse import parse_qs
from fyers_api import fyersModel
from fyers_api import accessToken

# streamlit run e:/python_Projects/streamlitOC/fyers_OptionsChain.py

@st.experimental_singleton
def getSymbol():
    fno_symbolList = pd.read_csv('http://public.fyers.in/sym_details/NSE_FO.csv')

    fno_symbolList.columns =  ['FyersToken', 'Name', 'Instrument', 'lot', 'tick', 'ISIN','TradingSession', 'Lastupdatedate', 'Expirydate', 'Symbol', 'Exchange', 'Segment','ScripCode','ScripName','x','strike','optiontype']
    fno_symbolList['Expirydate'] = pd.to_datetime(fno_symbolList['Expirydate'],unit='s').apply(lambda x: x.date())
    weeklyDf =fno_symbolList[(fno_symbolList['Instrument'].isin([14])) & (fno_symbolList['ScripName'] == 'NIFTY')]  # 14 for OPTIDX
    weeklyList = weeklyDf['Expirydate'].unique().tolist()
    weeklyList.sort()
    tokenmap = fno_symbolList[(fno_symbolList['Instrument'].isin([14])) & (fno_symbolList['ScripName'] == 'NIFTY') & (fno_symbolList['Expirydate'] == weeklyList[0])]
    return tokenmap


@st.experimental_singleton
def login():
    
    username = ''    
    password =''
    pin = ''    
    client_id = ''
    secret_key = ''

    redirect_uri = 'http://127.0.0.1:5000/'
    app_id = client_id[:-4]   

    session = accessToken.SessionModel(client_id=client_id, secret_key=secret_key, redirect_uri=redirect_uri,
                                    response_type='code', grant_type='authorization_code')
    response = session.generate_authcode()
    print(response)

    ses = requests.Session()

    payload = {"fy_id":f"{username}","password":f"{password}","app_id":"2","imei":"","recaptcha_token":""}
    res = ses.post('https://api.fyers.in/vagator/v1/login', json=payload).json()
    #print(res)
    request_key = res["request_key"]

    payload_pin = {"request_key":f"{request_key}","identity_type":"pin","identifier":f"{pin}","recaptcha_token":""}
    res_pin = ses.post('https://api.fyers.in/vagator/v1/verify_pin', json=payload_pin).json()
    ses.headers.update({
        'authorization': f"Bearer {res_pin['data']['access_token']}"
    })


    authParam = {"fyers_id":username,"app_id":client_id[:-4],"redirect_uri":redirect_uri,"appType":"100","code_challenge":"","state":"None","scope":"","nonce":"","response_type":"code","create_cookie":True}

    authres = ses.post('https://api.fyers.in/api/v2/token', json=authParam).json()

    url = authres['Url']
    print(url)
    parsed = urlparse.urlparse(url)
    auth_code = parse_qs(parsed.query)['auth_code'][0]
    session.set_token(auth_code)
    response = session.generate_token()
    token = response["access_token"]

    fyers = fyersModel.FyersModel(client_id=client_id, token=token, log_path='fv2/')
    print('Logged in')
    return fyers


def displayOC():
    
    fyers = login()
      
    res = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
    ltp = res['d'][0]['v']['lp']
    atmStrike = int(ltp/100)*100
    
    tokenmap = getSymbol()
    ocSymbols =  tokenmap[['Symbol','strike']]
    ocSymbols = ocSymbols[(ocSymbols.strike > atmStrike*0.95) & (ocSymbols.strike < atmStrike*1.05) ]
    ocSymbolList = ocSymbols['Symbol'].tolist()
    chunkArrays = np.array_split(ocSymbolList, len(ocSymbolList)/50 + 1)
    quoteList = []
    for symList in chunkArrays:
        data = {"symbols": ",".join(symList)}
        res = fyers.quotes(data)
        quoteList.extend(res['d'])
    ocDf = pd.json_normalize(quoteList)
    optionDf = ocDf[['v.symbol','v.lp','v.chp','v.ch','v.bid','v.ask' ,'v.volume']]
    optionDf.columns = ['Symbol','lp','chp','ch','bid','ask' ,'volume']
    optionDf = optionDf.merge(ocSymbols, on ='Symbol')
    ceoptionDf = optionDf[optionDf.Symbol.str.endswith('CE')]
    peoptionDf = optionDf[optionDf.Symbol.str.endswith('PE')]
    del peoptionDf['Symbol']
    del ceoptionDf['Symbol']
    peoptionDf = peoptionDf[peoptionDf.columns[::-1]]
    finalOCdf = ceoptionDf.merge(peoptionDf, on ='strike',suffixes=('_c', '_p'))
    finalOCdf.sort_values(by = 'strike',inplace = True)
    finalOCdf.reset_index(inplace=True, drop = True)
    
   
    
    def highlight_atm(x):
   
        if x.strike == atmStrike:
            return ['background-color: yellow']*13
        else:
            return ['background-color: white']*13
    s2 = finalOCdf.style.apply(highlight_atm, axis=1)


    st.table(s2)
   
  
    time.sleep(10)
    st.experimental_rerun()

if __name__ == "__main__":
    displayOC()




