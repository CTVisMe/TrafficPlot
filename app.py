import logging
import os

from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, render_template, request, url_for

from collector import collect_for_route, collect_travel_times, get_gmaps_client
from models import Measurement, Route, db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Railway Postgres URLs use "postgres://" but SQLAlchemy requires "postgresql://"
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    else:
        # Fall back to local SQLite for development
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data", "trafficplot.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        database_url = f"sqlite:///{db_path}"

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # --- Routes ---

    @app.route("/")
    def dashboard():
        routes = Route.query.order_by(Route.created_at.desc()).all()
        latest = {}
        for route in routes:
            latest[route.id] = {
                "outbound": Measurement.query.filter_by(
                    route_id=route.id, direction="outbound"
                )
                .order_by(Measurement.timestamp.desc())
                .first(),
                "return": Measurement.query.filter_by(
                    route_id=route.id, direction="return"
                )
                .order_by(Measurement.timestamp.desc())
                .first(),
            }
        return render_template("dashboard.html", routes=routes, latest=latest)

    @app.route("/route/<int:route_id>")
    def route_detail(route_id):
        route = Route.query.get_or_404(route_id)
        return render_template("route_detail.html", route=route)

    @app.route("/add", methods=["GET", "POST"])
    def add_route():
        if request.method == "POST":
            name = request.form["name"].strip()
            origin = request.form["origin"].strip()
            destination = request.form["destination"].strip()

            if not all([name, origin, destination]):
                return render_template(
                    "add_route.html", error="All fields are required."
                )

            route = Route(name=name, origin=origin, destination=destination)
            db.session.add(route)
            db.session.commit()

            # Immediately collect first measurement
            try:
                client = get_gmaps_client()
                collect_for_route(client, route)
            except Exception:
                logger.exception("Failed initial collection for route %s", name)

            return redirect(url_for("dashboard"))

        return render_template("add_route.html")

    @app.route("/route/<int:route_id>/toggle", methods=["POST"])
    def toggle_route(route_id):
        route = Route.query.get_or_404(route_id)
        route.active = not route.active
        db.session.commit()
        return redirect(url_for("dashboard"))

    @app.route("/route/<int:route_id>/delete", methods=["POST"])
    def delete_route(route_id):
        route = Route.query.get_or_404(route_id)
        db.session.delete(route)
        db.session.commit()
        return redirect(url_for("dashboard"))

    @app.route("/api/route/<int:route_id>/data")
    def route_data(route_id):
        Route.query.get_or_404(route_id)
        measurements = (
            Measurement.query.filter_by(route_id=route_id)
            .order_by(Measurement.timestamp)
            .all()
        )
        tz = ZoneInfo(os.environ.get("TZ", "America/New_York"))
        data = []
        for m in measurements:
            local_ts = m.timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
            data.append({
                "direction": m.direction,
                "travel_time_minutes": m.travel_time_minutes,
                "distance_km": m.distance_km,
                "timestamp": local_ts.isoformat(),
                "day_of_week": local_ts.weekday(),
                "hour": local_ts.hour,
            })
        return jsonify(data)

    @app.route("/api/collect", methods=["POST"])
    def trigger_collect():
        """Manual trigger for collection."""
        collect_travel_times(app)
        return jsonify({"status": "ok"})

    return app


app = create_app()

# Start scheduler (only in main process, not in reloader)
if not os.environ.get("WERKZEUG_RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        collect_travel_times,
        "cron",
        minute=0,
        args=[app],
        id="collect_travel_times",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — collecting every hour at :00")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
