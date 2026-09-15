from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from azure_connection import get_database_url
app = Flask(__name__)
# Local training placeholder. Configure a private secret before deployment.
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_ECHO'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'hide_parameters': True,
}

db = SQLAlchemy(app)


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


# Create database tables when this module is run or imported.
with app.app_context():
    db.create_all()


# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/dashboard')
        else:
            error = 'Invalid username or password'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    users = User.query.all()
    return render_template(
        'dashboard.html', users=users, current_user=session['username']
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/admin/create-user', methods=['POST'])
def create_user():
    # This lesson checks login only; an admin role check is still needed.
    if 'user_id' not in session:
        return redirect('/login')

    username = request.form.get('new_username')
    password = request.form.get('new_password')

    if User.query.filter_by(username=username).first():
        return redirect('/dashboard?error=User%20already%20exists')

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return redirect('/dashboard')


if __name__ == '__main__':
    # Use the development server and debugger for local practice only.
    app.run(debug=True, host='localhost', port=5000)
    