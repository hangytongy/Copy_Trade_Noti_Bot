import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta

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

def post_message(tele_chatid, message, tele_api):
    
    payload = {'chat_id' : tele_chatid, 'text' : message, 'parse_mode' : "HTML"}
    response = requests.post(tele_api, json=payload)
    
    if response.status_code == 200:
        print("post sucessful")
    else:
        print(f"error in posting {response}")

def main():
    
    for miner in wanted_miners:

        pairs = trading_pairs(miner)
        for pair in pairs:
            data = get_data(miner, pair)
            opens = get_open(data)
            if opens != []:
                for open in opens:
                    clean_data = open_cleaned(open)
                    if open['position_uuid'] not in miner_dic[miner]['uuid'] and not open['is_closed_position']:
                        print('new open data')
                        print(open['position_uuid'],clean_data)
                        intent = f"Miner : {clean_data['miner_hotkey']} \nTime : {clean_data['open_ms']} \nTrade_pair : {clean_data['trade_pair']} \nEntry Price : {clean_data['average_entry_price']} \nPosition Type : {clean_data['position_type']} \nLeverage : {clean_data['net_leverage']}"
                        message = u'\U00002744' + " <b>NEW OPEN:</b> \n " + intent
                        post_message(tele_chatid,message,tele_api)
                        miner_dic[miner]['uuid'].append(open['position_uuid'])
                        #uuid[open['position_uuid']] = [open['orders'][0]['order_uuid']]
                        uuid[open['position_uuid']] = [open['orders'][i]['order_uuid'] for i in range(0,len(open['orders']))]
                        print("order ids ", uuid[open['position_uuid']])
                    elif open['position_uuid'] in miner_dic[miner]['uuid'] and not open['is_closed_position']:
                        for order in open['orders']:
                            if order['order_uuid'] not in uuid[open['position_uuid']]:
                                print("new order")
                                print(order)
                                uuid[open['position_uuid']].append(order['order_uuid'])
                                clean_order = order_cleaned(order)
                                intent = f"Miner : {clean_data['miner_hotkey']} \nTime : {clean_order['processed_ms']} \nTrade_pair : {clean_data['trade_pair']} \nEntry Price : {clean_order['price']} \nPosition Type : {clean_order['order_type']} \nLeverage : {clean_order['leverage']}"
                                message = f"<b>ADD ORDER:</b> \n" + intent
                                post_message(tele_chatid,message,tele_api)
                                print("order ids ", uuid[open['position_uuid']])
                            
            closes = get_close(data)
            if closes != []:
                for close in closes:
                    close_uuid = close['position_uuid']
                    if close_uuid in miner_dic[miner]['uuid']:
                        clean_data_close = close_cleaned(close)
                        print('position close')
                        print(close['position_uuid'],clean_data_close)
                        intent = f"Miner : {clean_data_close['miner_hotkey']} \nTime : {clean_data_close['close_ms']} \nTrade_pair : {clean_data_close['trade_pair']} \nEntry Price : {clean_data_close['average_entry_price']} \nPosition Tyep : {clean_data_close['position_type']} \nLeverage : {clean_data_close['net_leverage']} \nReturns : {clean_data_close['return_at_close']}"
                        message = u'\U0001F4A8' + " <b>NEW CLOSE:</b> \n " + intent
                        post_message(tele_chatid,message,tele_api)
                        miner_dic[miner]['uuid'].remove(close_uuid)
                        del uuid[close_uuid]

def init_global():
    global tele_api
    global tele_chatid
    global wanted_miners
    global miner_dic
    global uuid

if __name__ == "__main__":

    init_global()
    
    tele_token = ""
    tele_api = f"https://api.telegram.org/bot{tele_token}/sendMessage"
    tele_chatid = "" 

    wanted_miners = []

    miners = get_miners()

    for miner in wanted_miners:
        if miner not in miners:
            print(f"{miner} not found")
            wanted_miners.remove(miner)
            
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
        time.sleep(60)