#!/usr/bin/env python
# coding=utf8

import requests
import json
import sys
from math import fabs

import datetime, threading, time
from pprint import pprint


headers = {'content-type': 'application/json',
   'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0'}

config_data = open('/home/ubuntu/config.json')
config = json.load(config_data)
config_data.close()

## -----------------------------------------------------------------------
## function about bts rpc
## -----------------------------------------------------------------------
auth = (config["bts_rpc"]["username"], config["bts_rpc"]["password"])
url = config["bts_rpc"]["url"]

asset_list = config["asset_list"]
init_asset_list = asset_list 
delegate_list = config["delegate_list"]
feed_list = []

def fetch_from_btc38():
  url="http://api.btc38.com/v1/ticker.php"
  while True:
     try:
       params = { 'c': 'btsx', 'mk_type': 'btc' }
       responce = requests.get(url=url, params=params, headers=headers)
       result = responce.json()
       price["BTC"].append(float(result["ticker"]["last"]))
       params = { 'c': 'btsx', 'mk_type': 'cny' }
       responce = requests.get(url=url, params=params, headers=headers)
       result = responce.json()
       price_cny = float(result["ticker"]["last"])
       price["CNY"].append(float(result["ticker"]["last"]))
       price["USD"].append(price_cny/rate_usd_cny)
       price["GLD"].append(price_cny/rate_xau_cny)
       price["EUR"].append(price_cny/rate_eur_cny)
       break
     except:
       e = sys.exc_info()[0]
       print "Error: fetch_from_btc38: retrying in 30 seconds", e
       time.sleep(30)
       continue

def fetch_from_bter():
  while True:
     try:
       url="http://data.bter.com/api/1/ticker/btsx_btc"
       responce = requests.get(url=url, headers=headers)
       result = responce.json()
       price["BTC"].append(float(result["last"]))
       url="http://data.bter.com/api/1/ticker/btsx_cny"
       responce = requests.get(url=url, headers=headers)
       result = responce.json()
       price_cny = float(result["last"])
       price["CNY"].append(float(result["last"]))
       price["USD"].append(price_cny/rate_usd_cny)
       price["GLD"].append(price_cny/rate_xau_cny)
       price["EUR"].append(price_cny/rate_eur_cny)
       break
     except:
       e = sys.exc_info()[0]
       print "Error: fetch_from_bter: retrying in 30 seconds", e 
       time.sleep(30)
       continue

def get_rate_from_yahoo():
  global headers
  global rate_usd_cny, rate_xau_cny, rate_eur_cny

  while True:
     try:
       url="http://download.finance.yahoo.com/d/quotes.csv"
       params = {'s':'USDCNY=X,XAUCNY=X,EURCNY=X','f':'l1','e':'.csv'}
       responce = requests.get(url=url, headers=headers,params=params)

       pos = posnext = 0
       posnext = responce.text.find("\n", pos)
       rate_usd_cny = float(responce.text[pos:posnext])
       print "Fetch: rate usd/cny", rate_usd_cny
       pos = posnext + 1
       posnext = responce.text.find("\n", pos)
       rate_xau_cny = float(responce.text[pos:posnext])
       print "Fetch: rate xau/cny", rate_xau_cny
       pos = posnext + 1
       posnext = responce.text.find("\n", pos)
       rate_eur_cny = float(responce.text[pos:posnext])
       print "Fetch: rate eur/cny", rate_eur_cny
       print
       break
     except:
       e = sys.exc_info()[0]
       print "Error: get_rate_from_yahoo:  try again after 30 seconds", e
       time.sleep(30)
       continue

def update_price(delegate,asset,price,feed):
      update_request = {
         "method": "wallet_publish_feeds",
         "params": [delegate, price, asset],
         "jsonrpc": "2.0",
         "id": 1
      }

      present  = datetime.datetime.now()
      feed_price  = feed['price']
      symbol      = feed['asset_symbol']
      last_update = feed['last_update']

      lu_yr  = int(last_update[0:4])
      lu_mn  = int(last_update[4:6])
      lu_dy  = int(last_update[6:8])
      lu_hr  = int(last_update[9:11])
      lu_min = int(last_update[11:13])
      lu_sec = int(last_update[13:15])
      lu_d   = datetime.date(lu_yr,lu_mn,lu_dy)
      lu_t   = datetime.time(lu_hr,lu_min,lu_sec)
      lu_dt  = datetime.datetime.combine(lu_d,lu_t)

      # Calculate Price Variance
      if (price > feed_price):
            diff = 100 - (round((feed_price / price) * 100,0))
      else:
            diff = 100 - (round((price / feed_price) * 100,0))

      # Calculate Time Since Last Update
      tm_df  = present-lu_dt
      tm_mx  = datetime.timedelta(hours=config['maxhours'])
		
      print "   Delegate Price Feed: ",symbol,feed_price
      print "         Current Price: ",asset,price
      print " BC Last Update String: ",last_update
      print "      Last Update Date: ",lu_dt
      print "     Current Date/Time: ",present
      print "     Time Since Update: ",str(tm_df)
      print " Max Hrs Before Update: ",str(tm_mx)
      print "        Price Variance: ",int(diff)
      print "    Max Price Variance: ",config['variance']
      print "           Update Feed: ",

      while True:
           try:
               # Publish Asset Price If Maximum Price Variance or Maximum Time Are Exceeded
               if ((int(diff) >= config['variance']) or (tm_df > tm_mx)):
                  print "Yes",
                  print "-",delegate, price_average[asset], asset
                  lst = []
                  #lst.append(asset.encode('utf-8'))
                  lst.append(asset)
                  lst.append(price_average[asset])
                  feed_list.append(lst)
               else:
                  print "No"
               print
               break

           except:
               e = sys.exc_info()[0]
               print "Warnning: Can't connect to rpc server or other error, (update_request) try again after 30 seconds", e
               time.sleep(30)

def update_feed(price, asset, delegate):

     headers = {'content-type': 'application/json'}
     feed_request = {
         "method": "blockchain_get_feeds_from_delegate",
         "params": [delegate],
         "jsonrpc": "2.0",
         "id": 1
     }
     while True:
        try:
           # Get Delegate Price Feeds
           responce = requests.post(url, data=json.dumps(feed_request), headers=headers, auth=auth)
           result   = json.loads(vars(responce)['_content'])
           lresult  = result['result']
           for i in lresult:
              if (asset == i['asset_symbol']): 
                 update_price(delegate,asset,price,i)

           break

        except:
           e = sys.exc_info()[0]
           print "Warnning: Can't connect to rpc server or other error, (get_feeds) try again after 30 seconds", e
	   time.sleep(30)


def fetch_price():
  for asset in init_asset_list:
    price[asset] = []

  fetch_from_btc38()
  fetch_from_bter()

  for delegate in delegate_list:
     for asset in asset_list:
       if len(price[asset]) == 0:
         print "Warning: can't get price of", asset
         continue
       price_average[asset] = sum(price[asset])/len(price[asset])
       update_feed(price_average[asset], asset, delegate)

     cmd_request = {
     		"method": "wallet_publish_feeds",
     		"params": [delegate, feed_list],
     		"jsonrpc": "2.0",
     		 "id": 1
     }
     try:
        if not feed_list:
	   print "No feeds to update"
 	else:
	   responce = requests.post(url, data=json.dumps(cmd_request), headers=headers, auth=auth)
           result = json.loads(vars(responce)["_content"])
	   print cmd_request


     except:
        e = sys.exc_info()[0]
        print "Warnning: Can't connect to rpc server or other error, (update_request):", e

print '=================', time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time())), '=================='

rate_usd_cny = 0.0
rate_xau_cny = 0.0
rate_eur_cny = 0.0
get_rate_from_yahoo()

price = {}
price_average = {}
price_average_last = {}

for asset in init_asset_list:
  price[asset] = []
  price_average[asset] = 0.0
  price_average_last[asset] = 0.0

fetch_price()

print '=================', time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time())), '=================='
print


