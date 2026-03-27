# TrafficPlot

A personal traffic monitoring app that tracks real-world travel times for your regular routes using the Google Maps API — so you can see exactly when traffic is bad and plan smarter.

**Live app:** [trafficplot-production.up.railway.app](https://trafficplot-production.up.railway.app/)

---

## What it does

- Add any routes you drive regularly (e.g. Home → Office)
- Automatically collects travel times in both directions every 15 minutes via the Google Maps Distance Matrix API
- Visualizes the data as:
  - **Weekly heatmap** — median travel time by day and hour
  - **Hourly box plots** — spread of travel times for any given day
  - **Time series** — full history of every measurement

## Tech stack

- **Backend:** Python / Flask
- **Database:** PostgreSQL (SQLite for local dev)
- **Scheduler:** APScheduler (background collection every 15 min)
- **Charts:** Plotly.js
- **Hosting:** [Railway](https://railway.app)

## Local development

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```

3. Run the app:
   ```bash
   flask run
   ```

The app will use SQLite locally and fall back gracefully if no Google Maps API key is set (collection will be skipped but the UI still works).

## Environment variables

| Variable | Description |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Google Maps Distance Matrix API key |
| `SECRET_KEY` | Flask secret key (any random string) |
| `DATABASE_URL` | PostgreSQL URL (auto-injected by Railway; omit for local SQLite) |
