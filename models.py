from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    origin = db.Column(db.String(500), nullable=False)
    destination = db.Column(db.String(500), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    measurements = db.relationship(
        "Measurement", backref="route", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Route {self.name}: {self.origin} -> {self.destination}>"


class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # "outbound" or "return"
    travel_time_minutes = db.Column(db.Float, nullable=False)
    distance_km = db.Column(db.Float, nullable=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (db.Index("idx_route_timestamp", "route_id", "timestamp"),)

    def __repr__(self):
        return f"<Measurement route={self.route_id} {self.direction} {self.travel_time_minutes:.1f}min>"
