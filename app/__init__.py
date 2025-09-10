# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


db = SQLAlchemy()
bcrypt = Bcrypt()

login_manager = LoginManager()
login_manager.login_view = 'login'

from app.models import User  # make sure your User model is imported
from app import login_manager



def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'supersecretkey'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    db.init_app(app)
    bcrypt.init_app(app)

    login_manager.init_app(app)
    
    # Import models
    from app import models

    with app.app_context():
        db.create_all()

    # Import routes and register
    from app.routes import register_routes
    register_routes(app)

    return app


