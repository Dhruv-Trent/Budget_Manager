# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt



db = SQLAlchemy()
bcrypt = Bcrypt()




def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'supersecretkey'
    


    db.init_app(app)
    bcrypt.init_app(app)


    # Import models
    from app import models

    with app.app_context():
        db.create_all()

    # Import routes and register
    from app.routes import register_routes
    register_routes(app)

    return app


