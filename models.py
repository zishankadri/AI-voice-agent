from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class CallSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    call_sid = db.Column(db.String(64), unique=True, nullable=False)
    order_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
