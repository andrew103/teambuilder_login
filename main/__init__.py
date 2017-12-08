from flask import Flask, jsonify, request, g, make_response
from flask import url_for, redirect, flash, render_template

from flask import session as login_session

from main.models import Base, User, PendingUser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import wraps

import random, string

import flask_login
from flask_login import LoginManager, login_user

from itsdangerous import URLSafeTimedSerializer

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#===================== INIT CODE ============================

engine = create_engine('sqlite:///user.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.secret_key = "userloginapplication"
app.debug = True

server = smtplib.SMTP('smtp.gmail.com', 587)

# ================= BEGIN LOGIN REQUIREMENT CODE ==============

@login_manager.user_loader
def load_user(user_id):
    '''
    Takes a unicode format user id and uses it to retrieve the respective user
    object to be used by the login_manager
    '''
    user = session.query(User).filter_by(id=int(user_id)).first()
    return user

# ================== END LOGIN REQUIREMENT CODE ===============

@app.route('/login', methods=['GET', 'POST'])
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))

    login_session['state'] = state

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pass']
        try:
            try:
                user = session.query(PendingUser).filter_by(email=email).first()
            except:
                user = session.query(User).filter_by(email=email).first()

            if user.verify_password(password):
                if request.form.get("remember_me"):
                    login_user(user, force=True, remember=True)
                else:
                    login_user(user, force=True)
                flash("You have logged in successfully " + user.name)
                user.is_authenticated = True
                return redirect(url_for('home')) # JSON object
            else:
                flash("You entered an incorrect password. Please try again")
                return redirect(url_for('login')) # JSON object
        except:
            flash("User does not exist. Please create an account")
            return redirect(url_for('signup')) # JSON object
    else:
        return render_template('login.html', STATE=state)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        flask_login.logout_user()
        flash("Logout Successful")
        return redirect(url_for('home'))
    else:
        return render_template('logout.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print(request.data)
    if request.method == 'POST':
        user = request.form['name']
        email = request.form['email']
        password = request.form['pass']
        confirm_code = generate_code()

        print(user+email+password)

        newUser = PendingUser(name=user, email=email, code=confirm_code)
        newUser.hash_password(password)

        session.add(newUser)
        session.commit()

        login_user(newUser, force=True)
        newUser.is_authenticated=True

        flash("Welcome "+user+". You have successfully signed up")

        msg = MIMEMultipart()
        msg['From'] = 'DoNotReply@teambuilder.com'
        msg['To'] = email
        msg['Subject'] = 'Email confirmation'
        body = render_template('email.html', name=user, code=confirm_code)
        msg.attach(MIMEText(body, 'html'))

        try:
            server.starttls()
        except:
            while True:
                try:
                    server.connect()
                    break
                except:
                    pass
            server.starttls()

        server.login('fbar620@gmail.com', 'fake_password')
        text = msg.as_string()
        print("Before email send")
        try:
            server.sendmail('DoNotReply@teambuilder.com', email, text)
        except:
            flash("Invalid email")
        server.quit()

        return jsonify(test=[1,2,3]) # JSON object
    else:
        # print(request.args['nameinput'])
        # print(request.args['emailinput'])
        # print(request.args['passinput'])
        return render_template('signup.html')

@app.route('/')
@app.route('/index')
def home():
    return render_template('index.html')

@app.route('/confirm', methods=['GET', 'POST'])
def confirm_email():
    if request.method == 'POST':
        user = request.form['user_id']
        code = request.form['code']

        try:
            user = session.query(PendingUser).filter_by(id=user).first()
        except:
            flash("User does not exist")

        if code == user.code:
            session.add(user)
            session.commit()

            flash("Account confirmed")
            return True # return JSON object with True in it

        return False
    else:
        return "GET OFF MY LAWN" ## PLACEHOLDER


def generate_code():
    code = ""
    for i in range(8):
        char = string.printable[random.randint(0, len(string.printable)-1)]
        code += char

    return code
