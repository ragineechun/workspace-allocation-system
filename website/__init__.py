from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    # Set SECRET_KEY as an environment variable in production
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Workspace  # Import Workspace model

    with app.app_context():
        db.create_all()
        seed_workspaces()  # Seed default workspaces

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')

def seed_workspaces():
    """Seed the database with default workspaces."""
    from .models import Workspace

    # List of default workspaces
    default_workspaces = [
        {"name": "Workspace 1","floor":"1", "capacity": 4, "amenities": "Wi-Fi, Whiteboard, Projector"},
        {"name": "Workspace 2", "floor":"1","capacity": 6, "amenities": "Wi-Fi, Monitor, AC"},
        {"name": "Workspace 3","floor":"1", "capacity": 10, "amenities": "Wi-Fi, Conference Setup"},
    ]

    # Add workspaces to the database if they don't already exist
    for workspace_data in default_workspaces:
        existing_workspace = Workspace.query.filter_by(name=workspace_data["name"]).first()
        if not existing_workspace:
            new_workspace = Workspace(
                name=workspace_data["name"],
                capacity=workspace_data["capacity"],
                amenities=workspace_data["amenities"],
            )
            db.session.add(new_workspace)
    db.session.commit()
    print("Default workspaces have been added.")
