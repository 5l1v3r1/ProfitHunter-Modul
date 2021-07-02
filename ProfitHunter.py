import ccxt
from discord_webhook import DiscordWebhook, DiscordEmbed
import json
from datetime import datetime
from time import sleep
import logging



with open ('settings.json') as config_file:
    config = json.load(config_file)
key = config['api-key']
secret = config['api-secret']
take_profit  = config['Percent_take_profit']
stop_loss  = config['Percent_stop_loss']
pairs = config['select_Coins']
sleeptime = config['interval_time']
discordwebhook = config['discord_webhook']
discord = config['discord']


exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
binance = exchange_class({'apiKey':key, 
 'secret':secret, 
 'timeout':30000, 
 'enableRateLimit':True, 
 'option':{'defaultMarket': 'futures'}, 
 'urls':{'api': {'public':'https://fapi.binance.com/fapi/v1', 
          'private':'https://fapi.binance.com/fapi/v1'}}})


#logging errors in errors.log
log_format = '%(levelname)s - %(asctime)s - %(message)s'
logging.basicConfig(filename='errors.log', filemode='a',
  level=(logging.ERROR),
  format=log_format)

class Profit:

    def __init__(self):
        self._TIMEOUT = 5

    def send_stoploss(self):
        url = discordwebhook
        webhook = DiscordWebhook(url=url)
        embed = DiscordEmbed(title=('Stop Loss reached!'), description='', color=242424)
        embed.set_timestamp()
        embed.add_embed_field(name='Symbol:' , value=(str(self.tickerSymbol)))
        embed.add_embed_field(name='Losed:' , value=(str(self.PnL)+'$'))
        embed.add_embed_field(name='COIN PRICE: ', value=(str(round(self.last,2))))
        webhook.add_embed(embed)
        webhook.execute()

    def fetch_ticker(self):
        tickerDump = binance.fetch_ticker(self.tickerSymbol)
        self.last = tickerDump['last']

    def look_filledOrders(self, symbol):
        coins = symbol
        open_positions = binance.fapiPrivateGetPositionRisk()
        for coin in coins:
            sleep(sleeptime)
            self.tradePair = coin
            symbolRaw = self.tradePair[:-4]
            self.tickerSymbol = symbolRaw + '/USDT'
            bot.fetch_ticker()
            for position in open_positions:
                if position['symbol'] == self.tradePair:
                    if float(position['positionAmt']) > 0.0:
                        self.open_position = True
                        self.position = True
                        self.side = 'long'
                        self.size = float(position['positionAmt'])
                        self.entry = float(position['entryPrice'])
                        self.PnL = round(float(position['unRealizedProfit']),3)
                        bot.take_profit(self.tradePair)
                    if float(position['positionAmt']) < 0.0:
                        self.open_position = True
                        self.position = True
                        self.side = 'short'
                        self.size = float(position['positionAmt'])
                        self.entry = float(position['entryPrice'])
                        self.PnL = round(float(position['unRealizedProfit']),3)
                        bot.take_profit(self.tradePair)
                    if float(position['positionAmt']) == 0:
                        self.open_position = False
                        self.side = None
                        self.size = 0
                        self.entry = 0
                else:
                    continue

    def take_profit(self, symbol):
        if self.side == 'long':
            print(self.tradePair,'Position is: LONG')
            self.takeprofit = self.entry + self.last * (take_profit / 100)
            self.stoploss = self.entry - self.last * (stop_loss / 100)
            bot.cancel_tp()
            if self.last <= self.stoploss:
                print('Stop Loss reached:',symbol,'SELL MARKET!')
                self.open_position = False
                binance.create_market_sell_order(self.tickerSymbol, abs(self.size))
                if discord:
                    bot.send_stoploss()
                self.open_position = False
        if self.side == 'short':
            print(self.tradePair,'Position is: Short')
            self.takeprofit = self.entry - self.last * (take_profit / 100)
            self.stoploss = self.entry + self.last * (stop_loss / 100)
            bot.cancel_tp()
            if self.last >= self.stoploss:
                print('Stop Loss reached:',symbol,'BUY MARKET!')
                self.open_position = False
                binance.create_market_buy_order(self.tickerSymbol, abs(self.size))
                if discord:
                    bot.send_stoploss()
                self.open_position = False

    def cancel_tp(self):
        openOrders = binance.fapiPrivateGetOpenOrders()
        self.orderPlace = False
        if openOrders:
            for orders in openOrders:
                if orders['symbol'] == self.tradePair:
                    if self.side == 'long':
                        if float(orders['origQty']) < abs(self.size) and orders['side'] == 'SELL':
                            print(self.tradePair,'Close Old Take Profit Order:', orders['orderId'])
                            binance.cancel_order(orders['orderId'], self.tickerSymbol)
                            sleep(0.5)
                            self.orderPlace = True
                            bot.long_profit()
                        else:
                            if int(orders['executedQty']) > 0:
                                print('Remove', orders['orderId'])
                                binance.cancel_order(orders['orderId'], self.tickerSymbol)
                                sleep(0.5)
                                self.orderPlace = True
                                bot.long_profit()
                            else:
                                self.orderPlace = True
                    else:
                        if self.side == 'short':
                            if float(orders['origQty']) < abs(self.size) and orders['side'] == 'BUY':
                                print(self.tradePair,'Close Old Take Profit Order')
                                binance.cancel_order(orders['orderId'], self.tickerSymbol)
                                sleep(0.5)
                                self.orderPlace = True
                                bot.short_profit()
                            else:
                                if int(orders['executedQty']) > 0:
                                    print(self.tradePair,'Close Old Take Profit Order:')
                                    binance.cancel_order(orders['orderId'], self.tickerSymbol)
                                    sleep(0.5)
                                    self.orderPlace = True
                                    bot.short_profit()
                                else:
                                    self.orderPlace = True
                        else:
                            self.orderPlace = True
                            print(self.tradePair,'Take Profit Order is OK!')
                    continue

        if self.orderPlace is False:
            if self.open_position is True:
                print( self.tradePair,'Create Profit Order')
                if self.side == 'long':
                    self.orderPlace = True
                    bot.long_profit()
                else:
                    self.orderPlace = True
                    bot.short_profit()
        else:
            pass

    def long_profit(self):
        params = {'reduceOnly':'true'}
        binance.create_limit_sell_order(self.tickerSymbol, abs(self.size), self.takeprofit, params)
        print("Place Profit SELL Order for",self.takeprofit,"$ at", self.tradePair)

    def short_profit(self):
        params = {'reduceOnly':'true'}
        binance.create_limit_buy_order(self.tickerSymbol, abs(self.size), self.takeprofit, params)
        print("Place Profit BUY Order for",self.takeprofit,"$ at", self.tradePair)

    def start_bot(self):
        print('Starting StopLossTakeProfit Modul!')
        while True:
            try:
                bot.look_filledOrders(pairs)
            except Exception as e:
                try:
                    logging.error(e)
                    sleep(sleeptime)
                finally:
                    e = None
                    del e

bot = Profit()
bot.start_bot()
