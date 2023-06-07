from MySQLdb import IntegrityError
from . import db
from . import mail
import re
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from functools import wraps
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
import requests
from flask_mail import Message
import random

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        pass_ = request.form['password']

        # Create cursor
        cur = db.connection.cursor()

        # Get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(pass_, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                result = cur.execute("SELECT balance FROM users WHERE username = %s", [username])
                data = cur.fetchone()
                balance = float(data['balance'])
                

                flash('You are now logged in', category='success')  
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect Password!', category='error')
                return render_template('login.html')

            # Close connection
            cur.close()
        else:
            flash('Username not found', category='error')
            return render_template('login.html')

    return render_template('login.html')


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        pass1 = request.form.get('password')
        pass2 = request.form.get('conpass')

        #regular expression for password validation
        regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$" 
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        username_pattern = "^[a-z0-9_]{3,15}$"

        if not re.match(username_pattern,username):
            flash('Invalid Username.', category='error')
        elif not re.match(email_pattern,email):
            flash('Invalid email address', category='error')
        elif pass1 != pass2:
            flash('Passwords don\'t match.', category='error')
        elif not re.match(regex, pass1):
            flash('Invalid password!', category='error')
        else:
            cur = db.connection.cursor()

            try:
                cur.execute("INSERT INTO users(username,email, password) VALUES(%s, %s, %s)",
                            (username, email,   sha256_crypt.encrypt(str(pass1))))

                db.connection.commit()

                cur.close()
                flash('account created!', category='success')
                return redirect(url_for('auth.login'))
            except IntegrityError:
                db.connection.rollback()
                flash('Username already exists!', category='error')
    return render_template("sign_up.html")


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', category='error')
            return redirect(url_for('auth.login'))
    return wrap

# Logout
@auth.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', category='warning')
    return redirect(url_for('auth.login'))

@auth.route('/forget-pass',methods=['GET', 'POST'])
def forget_pass():
    if request.method == 'POST':
        email = request.form.get('email')
        cur = db.connection.cursor()
        
        result = cur.execute(
            "SELECT email FROM users WHERE email = %s ", [email])

        
        if result>0:
           
           otp = random.randint(100000, 999999)
           session['otp']=otp
           data = cur.fetchone()
           email_db = data['email']
           session['email']=email_db
           msg = Message('Forgot Password : OTP', 
           sender='janvinirmal5@gmail.com', 
           recipients=[email_db])
           msg.body = "Hi, OTP to reset your password is : "+ str(otp)
           mail.send(msg)
           flash('OTP sent to registered mail id!',category="success")
           return redirect(url_for('auth.verify_otp'))
        else:
            flash('Please enter registerd email address!',category="warning")

    return render_template("forget-pass.html")

@auth.route('/verify-otp',methods=['GET', 'POST'])
def verify_otp():
    if request.method=='POST':
        otp_entered = request.form.get('otp')
        otp = session.get('otp')
        print(otp_entered,otp)
        if str(otp) == str(otp_entered):
            return render_template("change_pass.html")
        else:
            flash('enter valid otp!',category="error")
    return render_template("otp.html")

@auth.route('/changepass',methods=['GET', 'POST'])
def change_password():
    new_pass=request.form.get('newpass')
    new_pass_con=request.form.get('newpasscon')

    if new_pass==new_pass_con:
         email=session.get('email')
         cur = db.connection.cursor()
         cur.execute("UPDATE users SET password = %s WHERE email = %s ",(sha256_crypt.encrypt(str(new_pass)),email))
         db.connection.commit()
         cur.close()
         flash('password updated!',category="success")
         return redirect(url_for('auth.login'))
    else:
        flash("passwords dont match",category="error")

    return render_template("change_pass.html")

@auth.route('/profile',methods=['GET','POST'])
def profile():
    username=session.get('username')
    cur = db.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s",[username])
    data = cur.fetchone()
    db.connection.commit()
    cur.close()
    return render_template("profile.html",data=data)

         

         

        