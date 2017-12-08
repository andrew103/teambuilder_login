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

engine = create_engine('sqlite:///site.db')
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

                return jsonify(success=True, data=user.serialize)
            else:
                flash("You entered an incorrect password. Please try again")
                return jsonify(success=False, error="pass") # JSON object
        except:
            flash("User does not exist. Please create an account")
            return jsonify(success=False, error="user") # JSON object
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
    if request.method == 'POST':
        user = request.form['name']
        email = request.form['email']
        password = request.form['pass']
        confirm_code = generate_code()

        # check if user already exists
        if session.query(PendingUser).filter_by(email=email).first() or session.query(User).filter_by(email=email).first():
            return jsonify(success=False, error="exists")

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
        try:
            server.sendmail('DoNotReply@teambuilder.com', email, text)
        except:
            flash("Invalid email")
            return jsonify(success=False, error="email")

        server.quit()

        return jsonify(success=True, data=newUser.serialize) # JSON object
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
        pending_user_id = request.form['user_id']
        code = request.form['code']

        try:
            pending_user = session.query(PendingUser).filter_by(id=pending_user_id).first()
        except:
            flash("User does not exist")
            return jsonify(success=False, error="user")

        if code == pending_user.code:
            # create new user with the same attributes of pendinguser then delete pendinguser
            user = User(name=pending_user.name,
                        email=pending_user.email,
                        password_hash=pending_user.password_hash,
                        is_authenticated=pending_user.is_authenticated,
                        is_active=pending_user.is_active)
            session.add(user)
            session.delete(pending_user)
            session.commit()

            flash("Account confirmed")
            return jsonify(success=True, data=user.serialize) # return JSON object with True in it

        return jsonify(success=False, error="code")
    else:
        return jsonify(access="denied")


def generate_code():
    code = ""
    chars = string.ascii_letters + string.digits
    for i in range(8):
        char = chars[random.randint(0, len(chars)-1)]
        code += char

    return code
