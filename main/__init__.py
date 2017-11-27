from flask import Flask, jsonify, request, g, make_response
from flask import url_for, redirect, flash, render_template

from flask import session as login_session

from .models import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import wraps

import random, string

import flask_login
from flask_login import LoginManager, login_user

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
        email = request.form['emailinput']
        password = request.form['passinput']
        try:
            user = session.query(User).filter_by(email=email).first()
            if user.verify_password(password):
                if request.form['remember_me']:
                    login_user(user, force=True, remember=True)
                else:
                    login_user(user, force=True)
                flash("You have logged in successfully " + user.name)
                user.is_authenticated = True
                return redirect(url_for('showCatalog'))
            else:
                flash("You entered an incorrect password. Please try again")
                return redirect(url_for('login'))
        except:
            flash("User does not exist. Please create an account")
            return redirect(url_for('signup'))
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
        user = request.form['nameinput']
        email = request.form['emailinput']
        password = request.form['passinput']

        if password != request.form['confirmpass']:
            flash("Passwords don't match")
            return redirect(url_for('signup'))

        newUser = User(name=user, email=email)
        newUser.hash_password(password)

        session.add(newUser)
        session.commit()

        login_user(newUser, force=True)
        newUser.is_authenticated=True

        flash("Welcome "+user+". You have successfully signed up")
        return redirect(url_for('home'))
    else:
        return render_template('signup.html')


@app.route('/')
@app.route('/index')
def home():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
