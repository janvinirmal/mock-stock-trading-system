from datetime import timedelta
from flask import Flask
from flask_mysqldb import MySQL
from flask_mail import Mail, Message



db = MySQL()
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']='abc123'
    app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=15)


    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'janvi@3152'
    app.config['MYSQL_DB'] = 'flaskapp'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = 'janvinirmal5@gmail.com'
    app.config['MAIL_PASSWORD'] = 'mhqokpapndizzkbv'
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True

  
    db.init_app(app)
    mail.init_app(app)

    from .views import views
    from .auth import auth
    from .trade import trade
   
    app.register_blueprint(auth,url_prefix='/')
    app.register_blueprint(views,url_prefix='/')
    app.register_blueprint(trade,url_prefix='/')

    return app

