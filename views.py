from flask import Blueprint, render_template
import finnhub
views = Blueprint('views',__name__)

finnhub_client = finnhub.Client(api_key="cha9ml9r01qhe0r9uqf0cha9ml9r01qhe0r9uqfg")


@views.route('/')
def home():
    top_stocks = ['AAPL','MSFT','AMZN','NVDA','GOOG','TSLA','META','WMT','NTRS']
    info={}
    for symbol in top_stocks:
         prices=dict(finnhub_client.quote(symbol))
         curr_price=prices['c']
         prev_close=prices['pc']
         prices['diff']=((curr_price-prev_close)/prev_close)*100
         info[symbol]=prices
         

    return  render_template("home.html",info=info)