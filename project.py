from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash, g
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Coffee, CoffeeItem, User
from flask import session as login_session
from functools import wraps
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Coffee App"

engine = create_engine('sqlite:///coffee.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# login session
@app.route('/login')
def Login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return login session state
    return render_template('login.html', STATE=state)


# Required to Authorized
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("not allowed to access")
            return redirect(url_for('Login'))
    return decorated_function


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already \
            connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius: \
    150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("Successfully logged in %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    'except':
        return None


# JSON API
@app.route('/coffee/JSON')
def coffeeHomeJSON():
    coffeeHome = session.query(Coffee).all()
    return jsonify(CoffeeHome=[r.serialize for r in coffeeHome])


@app.route('/coffee/<int:coffee_id>/JSON')
def coffeeJSON(coffee_id):
    coffee = session.query(Coffee).filter_by(id=coffee_id).one()
    items = session.query(CoffeeItem).filter_by(coffee_id=coffee.id)
    return jsonify(CoffeeItem=[i.serialize for i in items])


@app.route('/coffee/<int:coffee_id>/<int:items_id>/JSON')
def coffeeItemJSON(coffee_id, items_id):
    coffee = session.query(Coffee).filter_by(id=coffee_id).one()
    items = session.query(CoffeeItem).filter_by(id=items_id).one()
    return jsonify(Item=[items.serialize])


# Home page
@app.route('/')
@app.route('/coffee')
def browseHome():
    coffee = session.query(Coffee).all()
    items = session.query(CoffeeItem).order_by(CoffeeItem.id.desc()).limit(4)
    # If user not login will render publicHomeCoffee else homeCoffee
    if 'username' not in login_session:
        return render_template('publicHome.html', coffee=coffee, items=items)
    else:
        return render_template('homeCoffee.html', coffee=coffee, items=items)


# Browse items inside the coffee
@app.route('/coffee/<int:coffee_id>')
def browseCoffee(coffee_id):
    menu = session.query(Coffee).all()
    coffee = session.query(Coffee).filter_by(id=coffee_id).one()
    items = session.query(CoffeeItem).filter_by(coffee_id=coffee.id)
    return render_template('coffeeMenu.html', menu=menu, coffee=coffee,
                           items=items)


# Add new item
@app.route('/coffee/new', methods=['GET', 'POST'])
@login_required
def addItem():
    # Get the entered data in the form
    if request.method == 'POST':
        addItem = CoffeeItem(name=request.form['name'],
                             description=request.form['description'],
                             price=request.form['price'],
                             coffee_id=request.form['coffee_id'],
                             user_id=login_session['user_id'])
        session.add(addItem)
        session.commit()
        flash("new item added successfully!")
        return redirect(url_for('browseHome'))
    else:
        return render_template('addItem.html')


# Browse the specific item
@app.route('/coffee/<int:coffee_id>/<int:items_id>')
def browseItem(coffee_id, items_id):
    coffee = session.query(Coffee).filter_by(id=coffee_id).one()
    items = session.query(CoffeeItem).filter_by(id=items_id).one()
    if 'username' not in login_session or \
       items.user_id != login_session['user_id']:
        # If user not login will render publicBrowseItem
        return render_template('publicBrowseItem.html', coffee=coffee,
                               items=items)
    else:
        # If user login will be authorized to Edit and delete the item
        return render_template('browseItem.html', coffee=coffee, items=items)


# Edit specific item
@app.route('/coffee/<int:coffee_id>/<int:items_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(coffee_id, items_id):
    editItem = session.query(CoffeeItem).filter_by(id=items_id).one()
    if editItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert("
        "'You are not authorized to edit."
        "Please create your own item in order to edit."
        "');}</script><body onload='myFunction()''>"
    # Get the entered data in the form
    if request.method == 'POST':
        if request.form['name']:
            editItem.name = request.form['name']

        if request.form['description']:
            editItem.description = request.form['description']

        if request.form['price']:
            editItem.price = request.form['price']

        if request.form['coffee_id']:
            editItem.coffee_id = request.form['coffee_id']
        session.add(editItem)
        session.commit()
        flash("item edited successfully!")
        return redirect(url_for('browseItem', coffee_id=coffee_id,
                                items_id=items_id))
    else:
        return render_template('editItem.html', coffee_id=coffee_id,
                               items_id=items_id, item=editItem)


# Delete item
@app.route('/coffee/<int:coffee_id>/<int:items_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(coffee_id, items_id):
    deleteItem = session.query(CoffeeItem).filter_by(id=items_id).one()
    if deleteItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert("
        "'You are not authorized to delete."
        "Please create your own item in order to delete."
        "');}</script><body onload='myFunction()''>"
    # Item to delete it
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash("item deleted successfully!")
        return redirect(url_for('browseCoffee', coffee_id=coffee_id))
    else:
        return render_template('deleteItem.html', coffee_id=coffee_id,
                               items_id=items_id, item=deleteItem)


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        flash('Successfully disconnected')
        return redirect(url_for('browseHome'))
    else:
        flash('Failed to revoke token for given user.')
        return redirect(url_for('browseHome'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
