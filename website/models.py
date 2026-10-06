from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy import Time
from datetime import datetime


class Note(db.Model):
  id=db.Column(db.Integer , primary_key=True)
  data = db.Column(db.String(10000))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id= db.Column(db.Integer , db.ForeignKey('user.id'))

class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(150), unique=True)
  password = db.Column(db.String(150))
  first_name = db.Column(db.String(150))
  role = db.Column(db.String(150))
  notes = db.relationship('Note')
  
class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.Integer, nullable=True)
    x = db.Column(db.Integer, nullable=True)  # for SVG positioning
    y = db.Column(db.Integer, nullable=True)
    capacity = db.Column(db.Integer, nullable=False)
    amenities = db.Column(db.String(255), nullable=True)
    


class Booking(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'))
  date = db.Column(db.Date, nullable=False)
  start_time = db.Column(db.Time, nullable=False)
  end_time = db.Column(db.Time, nullable=False)
  

  workspace = db.relationship('Workspace', backref='bookings', lazy=True)
  user = db.relationship('User', backref='bookings', lazy=True)


class Notification(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  message = db.Column(db.String(500))
  timestamp = db.Column(db.DateTime(timezone=True), default=func.now())


# in models.py
class ClassRoutine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    division = db.Column(db.String(50), nullable=False)  # e.g., Division 1
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    day = db.Column(db.String(10), nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)  # e.g., Slot 1
    period_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    subject = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('workspace.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    room = db.relationship('Workspace')

