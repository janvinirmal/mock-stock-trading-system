import datetime
from flask import Blueprint, flash, redirect, render_template,request,jsonify, url_for,session
import plotly.express as px
from plotly.offline import plot
import requests
import finnhub
from . import db
from . import views

finnhub_client = finnhub.Client(api_key="cha9ml9r01qhe0r9uqf0cha9ml9r01qhe0r9uqfg")
trade = Blueprint('trade', __name__, url_prefix='/')

@trade.before_request
def complete_pending_orders():
     now = datetime.datetime.now()
     weekday = now.weekday()
     hour = now.hour
     if session.get('username',None) != None:
          username = session.get('username',None)
          cur = db.connection.cursor() 
          cur.execute("SELECT * FROM orders WHERE status='pending' AND user_id = %s AND order_type='market_price'", [username])
          rows = cur.fetchall()

          total = 0
          for row in rows:
               ticker=row['ticker']
               quantity = float(row['quantity'])
               prices=dict(finnhub_client.quote(ticker))
               price=prices.get('c')
               total += price * quantity
               order_id=row['order_id']
               current_timestamp = datetime.datetime.now()
               formatted_timestamp = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
               cur.execute("UPDATE orders SET order_time = %s WHERE order_id = %s",(formatted_timestamp,order_id))
               cur.execute("UPDATE orders SET status = 'success' WHERE order_id = %s",[order_id])
               db.connection.commit()


          cur.execute("SELECT balance from users WHERE username=%s;",[username])
          data = cur.fetchone()
          balance = float(data['balance'])
          updated_balance = balance - total
          cur.execute("UPDATE users SET balance = %s WHERE username = %s",(updated_balance,username))
          db.connection.commit()
          cur.close()
          
                    
@trade.route('/searchstock',methods=["POST", "GET"])
def redirect_to_search():
      if request.method == 'POST' : 
          symbol=str(request.form['symbol']).upper()
          session['symbol'] = symbol
          if finnhub_client.company_profile2(symbol=symbol) == {} or symbol=='':
               flash('Invalid symbol!', category='error')
          else:
               return redirect(url_for('trade.search', symbol=symbol))

@trade.route('/searchstock/<symbol>',methods=["POST", "GET"])
def search(symbol):
     information = dict(finnhub_client.company_profile2(symbol=symbol))
     session['company_name']=information.get('name')
     prices=dict(finnhub_client.quote(symbol))
     url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol='+symbol+'&outputsize=full&apikey=HCWSV4D09YCJ1DKT'
     r = requests.get(url)
     data = r.json()

     url2 = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol='+symbol+'&apikey=HCWSV4D09YCJ1DKT'
     r = requests.get(url2)
     overview = dict(r.json())
     date = data['Time Series (Daily)']
     high = [float(data['Time Series (Daily)'][x]['2. high']) for x in date]

     fig = px.line(data, x=data['Time Series (Daily)'].keys(), y=high,  color_discrete_sequence=['#142440'])

     fig.update_xaxes(
     rangeslider_visible=False,
     rangeselector=dict(
          buttons=list([
               dict(count=1, label="1m", step="month", stepmode="backward"),
               dict(count=6, label="6m", step="month", stepmode="backward"),
               dict(count=1, label="YTD", step="year", stepmode="todate"),
               dict(count=1, label="1y", step="year", stepmode="backward"),
               dict(step="all")
          ])
     )
     )

     # Define the buttons first
     buttons = [
     dict(
          args=[{"yaxis.range": [min(high), max(high)]}],
          label="Full",
          method="relayout"
     ),
     dict(
          args=[{"yaxis.range": [min(high), max(high) * 0.75]}],
          label="75%",
          method="relayout"
     ),
     dict(
          args=[{"yaxis.range": [min(high), max(high) * 0.5]}],
          label="50%",
          method="relayout"
     ),
     dict(
          args=[{"yaxis.range": [min(high), max(high) * 0.25]}],
          label="25%",
          method="relayout"
     ),
     ]

     # Update the updatemenus with the defined buttons
     fig.update_layout(
     updatemenus=[dict(buttons=buttons, direction="down", showactive=True)],
     xaxis=dict(showgrid=False),
     yaxis=dict(showgrid=False),
     plot_bgcolor='white',
     width=1200, height=400
     )

     plot1 = plot(fig, output_type='div')

     return render_template("trade.html",information=information,plot1=plot1,prices=prices,overview=overview)

@trade.route('/buy',methods=["POST", "GET"])
def buystocks():
     symbol=session.get('symbol', None)
     username = session.get('username',None)
     name = session.get('company_name',None)
     quantity = int(request.form['quantity'])
     type=request.form.get('order_type')
     price=float(request.form['price'])
     cur = db.connection.cursor() 
     result = cur.execute("SELECT balance FROM users WHERE username = %s", [username])
     data = cur.fetchone()
     balance = float(data['balance'])
    
     if balance>(quantity*price):
          updated_balance = balance - (quantity*price)
          now = datetime.datetime.now()
          weekday = now.weekday()
          hour = now.hour
          minute = now.minute
          if weekday < 5 and (hour > 9 or (hour == 9 and minute >= 30)) and hour < 20 and type=="market_price":
                cur.execute("INSERT INTO orders (`user_id`, `ticker`, `order_type`, `quantity`, `price`, `status`,`trade_type`,`company_name`) VALUES (%s,%s,%s,%s,%s,'success','buy',%s);",(username,symbol,type,quantity,price,name)) 
                cur.execute("UPDATE users SET balance = %s WHERE username = %s;",(updated_balance,username))  
          else:
                cur.execute("INSERT INTO orders (`user_id`, `ticker`, `order_type`, `quantity`, `price`, `status`,`trade_type`,`company_name`) VALUES (%s,%s,%s,%s,%s,'pending','buy',%s);",(username,symbol,type,quantity,price,name))
          db.connection.commit()
          cur.close()
          flash('order placed!',category='success')
     else:
          flash('Insufficient Balance!',category='error')
    
     return redirect(url_for('trade.search',symbol=symbol))
   
@trade.route('/history',methods=["POST", "GET"])
def trade_history():

     gain={}
     username = session.get('username',None)

     cur = db.connection.cursor() 
     cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY order_time DESC", [username])
     rows = cur.fetchall()
     cur.close()

     for row in rows:
          ticker=row['ticker']
          id=row['order_id']
          prices=dict(finnhub_client.quote(ticker))
          curr_price=prices['c']
          gain[id]=((curr_price-row['price'])/row['price'])*100


     return render_template("history.html",rows=rows,gain=gain)

@trade.route('/profile',methods=["POST","GET"])
def show_profile():

     return render_template("profile.html")   
    

@trade.route('/sell',methods=["POST","GET"])
def sellstock():
     ticker = request.args.get('ticker')
     id = request.args.get('id')
     information = dict(finnhub_client.company_profile2(symbol=ticker))
     prices=dict(finnhub_client.quote(ticker))
     url2 = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol='+ticker+'&apikey=HCWSV4D09YCJ1DKT'
     r = requests.get(url2)
     overview = dict(r.json())
     cur = db.connection.cursor() 
     cur.execute("SELECT * FROM orders WHERE order_id = %s",[id])
     data=cur.fetchone()
     cur.close()
          
     return render_template("sell.html",ticker=ticker,information=information,prices=prices,overview=overview,data=data)


  
@trade.route('/holding',methods=["POST", "GET"])
def current_holding():
     gain={}
     username = session.get('username',None)

     cur = db.connection.cursor() 
     cur.execute("SELECT SUM(price * quantity) AS total_sum FROM current_holding WHERE user_id = %s;",[username])
     ans = cur.fetchone()
     total=ans['total_sum']
     cur.execute("SELECT * FROM users WHERE username = %s",[username])
     result=cur.fetchone()
     cur.execute("SELECT * FROM current_holding WHERE user_id = %s", [username])
     rows = cur.fetchall()
     cur.close()

     for row in rows:
          ticker=row['ticker']
          id=row['order_id']
          prices=dict(finnhub_client.quote(ticker))
          curr_price=prices['c']
          r_price=float(row['price'])
          gain[id]=((curr_price-r_price)/r_price)*100
     
     if total==None:
          total=0

     return render_template("holding.html",rows=rows,gain=gain,total=total,result=result)

@trade.route('/sell-check',methods=["POST", "GET"])
def sell_check():
      id = request.args.get('id')
      quantity = int(request.form['quantity'])
      price=float(request.form['price'])    
      cur = db.connection.cursor() 
      cur.execute("SELECT * FROM orders WHERE order_id = %s",[id])
      data=cur.fetchone()
      cur.execute("SELECT * FROM current_holding WHERE order_id = %s",[id])
      curr_holding=cur.fetchone()

      quantity_r = curr_holding['quantity']
      price_buy=float(curr_holding['price'])

      if quantity > quantity_r:
           flash('Quantity exceeded',category="error")
           return redirect(url_for('trade.sellstock',ticker=data['ticker'],id=id))
      else:
          cur.execute("INSERT INTO orders (`user_id`, `ticker`, `order_type`, `quantity`, `price`, `status`,`trade_type`,`company_name`) VALUES (%s,%s,%s,%s,%s,'success','sell',%s);",(data['user_id'],data['ticker'],'market',quantity,price,data['company_name'])) 
          gain=(price - price_buy)*quantity
          added_balance= price*quantity
          cur.execute("SELECT * FROM users WHERE username=%s",[data['user_id']])
          result = cur.fetchone()
          balance = result['balance']
          gain_given = result['gain']
          cur.execute("UPDATE users SET balance = %s, gain=%s WHERE username=%s",((balance+added_balance),(gain_given+gain),data['user_id']))
          if quantity_r==quantity:
               cur.execute("DELETE FROM current_holding WHERE order_id =%s",[id])
          else:    
               cur.execute("UPDATE current_holding SET quantity = %s WHERE order_id = %s",((quantity_r-quantity),id))
          flash('order executed!',category="success")

          db.connection.commit()
          cur.close()
          
          return redirect(url_for('views.home'))
      


           
          

