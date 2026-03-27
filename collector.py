import logging
import os
from datetime import datetime, timezone

import googlemaps

from models import db, Route, Measurement

logger = logging.getLogger(__name__)


def get_gmaps_client():
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable not set")
    return googlemaps.Client(key=api_key)


def collect_for_route(client, route):
    """Collect travel times for both directions of a route."""
    pairs = [
        ("outbound", route.origin, route.destination),
        ("return", route.destination, route.origin),
    ]
    now = datetime.now(timezone.utc)

    for direction, origin, destination in pairs:
        try:
            result = client.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode="driving",
                departure_time="now",
            )

            element = result["rows"][0]["elements"][0]
            if element["status"] != "OK":
                logger.warning(
                    "API returned status %s for route %s (%s)",
                    element["status"],
                    route.name,
                    direction,
                )
                continue

            # Prefer duration_in_traffic when available
            if "duration_in_traffic" in element:
                duration_seconds = element["duration_in_traffic"]["value"]
            else:
                duration_seconds = element["duration"]["value"]

            distance_meters = element["distance"]["value"]

            measurement = Measurement(
                route_id=route.id,
                direction=direction,
                travel_time_minutes=duration_seconds / 60.0,
                distance_km=distance_meters / 1000.0,
                timestamp=now,
            )
            db.session.add(measurement)
            logger.info(
                "Recorded %s %s: %.1f min, %.1f km",
                route.name,
                direction,
                measurement.travel_time_minutes,
                measurement.distance_km,
            )

        except Exception:
            logger.exception(
                "Error collecting %s for route %s", direction, route.name
            )

    db.session.commit()


def collect_travel_times(app):
    """Collect travel times for all active routes."""
    with app.app_context():
        routes = Route.query.filter_by(active=True).all()
        if not routes:
            logger.info("No active routes to collect")
            return

        try:
            client = get_gmaps_client()
        except RuntimeError:
            logger.error("Google Maps API key not configured, skipping collection")
            return

        logger.info("Collecting travel times for %d routes", len(routes))
        for route in routes:
            collect_for_route(client, route)
        logger.info("Collection complete")
