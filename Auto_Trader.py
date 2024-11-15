import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time
from datetime import datetime, timedelta
import os

api_key = ''
api = ''

def get_miners():
    url = "http://34.89.151.29/miners"
    response = requests.get(url)
    miners = response.json()
    return miners

def trading_pairs(miner):
    url = f"http://34.89.151.29/miner/pairs?address={miner}"
    response = requests.get(url)
    pairs = response.json()
    return pairs

def get_data(miner,pair):
    url = f"http://34.89.151.29/miner/positions?address={miner}&pairs={pair}"
    response = requests.get(url)
    text = response.json()
    return text

def get_open(text):
    open = text['open']
    return open   

def get_close(text):
    close = text['closed']
    return close

def close_cleaned(close):
    col = ['miner_hotkey','close_ms','trade_pair','average_entry_price','position_type','net_leverage','return_at_close']
    selected_data = {key:close[key] for key in col}
    selected_data['trade_pair'] = selected_data['trade_pair'][0]
    selected_data['close_ms'] = (datetime.fromtimestamp(selected_data['close_ms']/1000) +timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    return selected_data 

def open_cleaned(open):

    col = ['miner_hotkey','open_ms','trade_pair','average_entry_price', 'position_type','net_leverage']
    selected_data = {key: open[key] for key in col}
    selected_data['trade_pair'] = selected_data['trade_pair'][0]
    selected_data['open_ms'] = (datetime.fromtimestamp(selected_data['open_ms']/1000)+timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    return selected_data 

def order_cleaned(order):
    col = ['processed_ms', 'order_type', 'price', 'leverage']
    selected_data = {key : order[key] for key in col}
    selected_data['processed_ms'] = (datetime.fromtimestamp(selected_data['processed_ms']/1000)+timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    return selected_data

def close_orders(close):
    col = ['processed_ms','order_type','price','leverage']
    j = []
    for order in close['orders']:
        selected_data = {key : order[key] for key in col}
        selected_data['processed_ms'] = (datetime.fromtimestamp(selected_data['processed_ms']/1000)+timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        j.append(selected_data)
    return j

def close_format(data):
    f = ""
    for entry in data:
        a=f"Processed Time: {entry['processed_ms']}\n"
        b=f"Order Type: {entry['order_type']}\n"
        c=f"Price: {entry['price']}\n"
        d=f"Leverage: {entry['leverage']}\n"
        e=f"-" * 40 + "\n"
        f = f + a + b + c + d + e
    return f

def post_message(tele_chatid, message, tele_api):
    
    payload = {'chat_id' : tele_chatid, 'text' : message, 'parse_mode' : "HTML"}
    response = requests.post(tele_api, json=payload)
    
    if response.status_code == 200:
        print("post sucessful")
    else:
        print(f"error in posting {response}")

def points_change(close):
    try:
        for orders in close['orders']:
            print(orders)
        if float(close['return_at_close']) > 1:
            point = 1
        else:
            point = 0
        print(point)
        return point
    except Exception as e:
        print(e)

def update_point(close,point,csv_file):
    miner = close['miner_hotkey']
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"error {e}")

    if miner in df['miner'].tolist():
        current_points = df.loc[df['miner'] == miner, 'points'].iloc[0]
        new_points = current_points + point
        df.loc[df['miner'] == miner, 'points'] = new_points

        current_order = df.loc[df['miner'] == miner, 'total_orders'].iloc[0]
        new_total_order = current_order + 1
        df.loc[df['miner']==miner, 'total_orders'] = new_total_order
    else:
        new_row = pd.DataFrame({'miner': [miner], 'points': [point], 'total_orders': [1]})
        df = pd.concat([df, new_row], ignore_index=True)
        new_points = point
        new_total_order = 1
        
    df.to_csv(csv_file, index=False)
    print(f"points updated for miner {miner}")

    points = (new_points/new_total_order)*100
    return points

def get_csv_direct():
    current_directory = os.getcwd()
    csv_path = os.path.join(current_directory,'miners.csv')
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns = ['miner','points'])
        df.to_csv(csv_path,index=False)
        print("csv created")
    return csv_path

def get_points(miner,csv_path):
    df = pd.read_csv(csv_path)
    if miner in df['miner'].tolist():
        points = df.loc[df['miner']==miner, 'points'].iloc[0]
        total_orders = df.loc[df['miner']==miner, 'total_orders'].iloc[0]
        points = (points/total_orders)*100
    else:
        points = 0

    return points

def init_global():
    global tele_api
    global tele_chatid
    global wanted_miners
    global miner_dic
    global uuid
    global account_id

def main():

    csv_path = get_csv_direct()
    
    for miner in wanted_miners:

        pairs = ['AUD_USD','AUD_CAD','EUR_CAD','EUR_NZD','USD_JPY','AUD_NZD','NZD_USD','USD_CAD','EUR_GBP','NZD_CAD','EUR_USD','AUD_JPY']
        for pair in pairs:
            data = get_data(miner, pair)
            opens = get_open(data)
            if opens != []:
                for open in opens:
                    clean_data = open_cleaned(open)
                    if open['position_uuid'] not in miner_dic[miner]['uuid'] and not open['is_closed_position']:
                        print('new open data')
                        print(open['position_uuid'],clean_data)
                        trigger_trade(account_id,clean_data['net_leverage'],pair)
                        points = get_points(clean_data['miner_hotkey'], csv_path)
                        intent = f"Miner : {clean_data['miner_hotkey']} \nSuccess Rate : {points} \nTime : {clean_data['open_ms']} \nTrade_pair : {clean_data['trade_pair']} \nEntry Price : {clean_data['average_entry_price']} \nPosition Type : {clean_data['position_type']} \nLeverage : {clean_data['net_leverage']}"
                        message = u'\U00002744' + " <b>NEW OPEN:</b> \n " + intent
                        post_message(tele_chatid,message,tele_api)
                        miner_dic[miner]['uuid'].append(open['position_uuid']
                        uuid[open['position_uuid']] = [open['orders'][i]['order_uuid'] for i in range(0,len(open['orders']))]
                        print("order ids ", uuid[open['position_uuid']])
                    elif open['position_uuid'] in miner_dic[miner]['uuid'] and not open['is_closed_position']:
                        for order in open['orders']:
                            if order['order_uuid'] not in uuid[open['position_uuid']]:
                                print("new order")
                                print(order)
                                trigger_trade(account_id,clean_data['net_leverage'],pair)                       
                                uuid[open['position_uuid']].append(order['order_uuid'])
                                clean_order = order_cleaned(order)
                                points = get_points(clean_data['miner_hotkey'], csv_path)
                                intent = f"Miner : {clean_data['miner_hotkey']} \nSuccess Rate : {points}  \nTime : {clean_order['processed_ms']} \nTrade_pair : {clean_data['trade_pair']} \nEntry Price : {clean_order['price']} \nPosition Type : {clean_order['order_type']} \nLeverage : {clean_order['leverage']}"
                                message = f"<b>ADD ORDER:</b> \n" + intent
                                post_message(tele_chatid,message,tele_api)
                                print("order ids ", uuid[open['position_uuid']])
                            
            closes = get_close(data)
            if closes != []:
                for close in closes:
                    close_uuid = close['position_uuid']
                    if close_uuid in miner_dic[miner]['uuid']:
                        
                        #close trade on oanda
                        close_trade(account_id,pair)  
                                                        
                        #points update
                        points = points_change(clsoe)
                        new_points = update_point(close,points,csv_path)
                        
                        #clean data and post to tele
                        clean_data_close = close_cleaned(close)
                        clean_data_close_orders = close_orders(close)
                        print('position close')
                        print(close['position_uuid'],clean_data_close)               
                        intent = f"Miner : {clean_data_close['miner_hotkey']} \nTime : {clean_data_close['close_ms']} \nTrade_pair : {clean_data_close['trade_pair']} \nEntry Price : {clean_data_close['average_entry_price']} \nPosition Type : {clean_data_close['position_type']} \nLeverage : {clean_data_close['net_leverage']}"
                        intent2 = f"---Orders---\n"
                        intent3 = close_format(clean_data_close_orders)
                        intent4 = f"\n <b>Success Rate : {new_points}</b>\n"
                        message = u'\U0001F4A8' + " <b>NEW CLOSE:</b> \n " + intent + "\n\n" + intent2 + intent3 + intent4
                        post_message(tele_chatid,message,tele_api)
                        miner_dic[miner]['uuid'].remove(close_uuid)
                        del uuid[close_uuid]
                        print(uuid)

def run_req(endpoint,params = None):
    url = api+endpoint
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Send the request
    response = requests.get(url, headers=headers,params=params)

    # Check the response status code and print the response
    if response.status_code == 200:
        print("Success")
    else:
        print("Error:", response.status_code, response.text)
        
    return response.json()

def place_trade(account_id,body):
    url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/orders"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Send the request
    response = requests.post(url, headers=headers, data=json.dumps(body))

    # Check the response status code and print the response
    if response.status_code == 201:
        print("Open Order created successfully:")
        tx = response.json()['orderFillTransaction']
        print(f"order id : {tx['orderID']} \nPair : {tx['instrument']} \nUnits : {tx['units']} \nPrice : {tx['price']}")
    else:
        print("Error:", response.status_code, response.text)
        
    return response.json()

def close_trade(account_id,pair):
    url = f"https://api-fxpractice.oanda.com/v3/accounts/{account_id}/positions/{pair}/close"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payloads = ["longUnits", "shortUnits"]
    
    for i in range(2):
        try:
            payload = { payloads[i] : "ALL"}

            # Send the request
            response = requests.put(url, headers=headers, json = payload)

            # Check the response status code and print the response
            if response.status_code == 200:
                print("Close Order created successfully:")

                if payloads[i] == "longUnits":
                    tx = response.json()['longOrderFillTransaction']
                    print(f"Pair : {tx['instrument']} \nUnits {tx['units']} \nPirce : {tx['price']} \nPnL {tx['pl']}")
                    
                else:
                    tx = response.json()['shortOrderFillTransaction']
                    print(f"Pair : {tx['instrument']} \nUnits {tx['units']} \nPirce : {tx['price']} \nPnL {tx['pl']}")
                
            else:
                print("Error:", response.status_code, response.text)
        except Exception as e:
            print(e)
        
def trigger_trade(account_id,leverage,pair):
    units = leverage * 100
    
    body = {  
        "order": {
        "units": str(units),
        "instrument": pair,
        "timeInForce": "FOK",
        "type": "MARKET",
        "positionFill": "DEFAULT"
      }
    }
    
    place_trade(account_id,body)

def get_account_id():
    endpoint = '/v3/accounts'
    account_id = run_req(endpoint)['accounts'][0]['id']
    return account_id

def get_account_summary(account_id):
    endpoint = f'/v3/accounts/{account_id}/summary'
    response = run_req(endpoint)
    print(response)
    
def get_instruments(account_id):
    endpoint = f'/v3/accounts/{account_id}/instruments'
    instruments = run_req(endpoint)
    return instruments

def get_orders(account_id):
    endpoint = f'/v3/accounts/{account_id}/orders'
    orders = run_req(endpoint)
    return orders

def get_pending_orders(account_id):
    endpoint = f'/v3/accounts/{account_id}/pendingOrders'
    pending_orders = run_req(endpoint)
    return pending_orders

def cancel_order(account_id,order_id):
    endpoint = f'/v3/accounts/{account_id}/orders/{order_id}/cancel'
    cancel_order = run_req(endpoint)
    return cancel_order
    
def get_positions(account_id):
    endpoint = f'/v3/accounts/{account_id}/openPositions'
    positions = run_req(endpoint)
    return positions

def get_candles(pair):
    endpoint = f'/v3/instruments/{pair}/candles'
    candles = run_req(endpoint)
    
    df = {'time': [x['time'] for x in candles['candles']],
          'close': [float(x['mid']['c']) for x in candles['candles']]
         }
    
    df = pd.DataFrame(df)
    df['time'] = pd.to_datetime(df['time'])
    
    # Set the figure size
    plt.figure(figsize=(10, 6))  # Adjust the width and height as needed

    # Plot the data
    plt.plot(df['time'], df['close'])

    # Rotate x-axis labels by 45 degrees
    plt.xticks(rotation=45)

    # Add axis labels and title
    plt.xlabel("Time")
    plt.ylabel("Close Price")
    plt.title(f"Close Price Over Time for {pair}")

    # Display the plot
    plt.show()

if __name__ == "__main__":

    init_global()
    
    tele_token = ""
    tele_api = f"https://api.telegram.org/bot{tele_token}/sendMessage"
    tele_chatid = "" 
    
    #get oanda account id
    account_id = get_account_id()
    
    wanted_miners = ['5HE4v4d2ShWpsWeasynVaawvBjRcZsLX2sd5MGPiwoJfywir']
    #'5G9yGe6TEDxx7wD2mpM2XSu8P7gVt6wwUvuXRrHGAYJDA955','5FUbUjTuSrcUbDKTWWbjiyY8QTJS5c9nvWseLSopCFJDju43'

            
    miner_dic = {miner : {'uuid':[]} for miner in wanted_miners}

    uuid = {}

    message = "----<b>INITIALIZING SUBNET8 BOT</b>----\n\n<b>Nomaclatures</b>\nNEW OPEN: Newly opened position\nADD ORDER: Add/Reduce current position\nNEW CLOSE: Position fully closed\n\nfirst new noti shows exisiting positions"
    post_message(tele_chatid,message,tele_api)
    
    while True:
        try:
            main()
        except Exception as e:
            message = f"error {e}"
            post_message(tele_chatid,message,tele_api)
        time.sleep(1)
