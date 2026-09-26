import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crisislens.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


@app.context_processor
def inject_commit_id():
    commit_id = os.getenv("RENDER_GIT_COMMIT", "local")
    return {"commit_id": commit_id[:7]}


class Crisis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


def ensure_schema():
    """Add new columns to an existing SQLite database if needed."""
    inspector = inspect(db.engine)
    columns = {
        column["name"]
        for column in inspector.get_columns("crisis")
    }

    if "published_at" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE crisis "
                    "ADD COLUMN published_at DATETIME"
                )
            )


with app.app_context():
    db.create_all()
    ensure_schema()


def get_date_range(range_key):
    """Return UTC-naive start/end datetimes for the selected range."""
    india_tz = ZoneInfo("Asia/Kolkata")

    now_utc = datetime.now(timezone.utc)
    now_india = now_utc.astimezone(india_tz)

    today = now_india.date()

    if range_key == "today":
        start_date = today
        end_date = today + timedelta(days=1)

    elif range_key == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = today

    elif range_key == "7days":
        start_date = today - timedelta(days=6)
        end_date = today + timedelta(days=1)

    else:
        return None, None

    start_india = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=india_tz
    )

    end_india = datetime.combine(
        end_date,
        datetime.min.time(),
        tzinfo=india_tz
    )

    start_utc = start_india.astimezone(timezone.utc)
    end_utc = end_india.astimezone(timezone.utc)

    return (
        start_utc.replace(tzinfo=None),
        end_utc.replace(tzinfo=None)
    )


@app.route("/")
def home():
    range_key = request.args.get("range", "today")

    query = Crisis.query

    if range_key != "all":
        start_date, end_date = get_date_range(range_key)

        if start_date and end_date:
            query = query.filter(
                Crisis.published_at >= start_date,
                Crisis.published_at < end_date
            )

    crises = query.order_by(
        Crisis.published_at.desc(),
        Crisis.created_at.desc()
    ).all()

    return render_template(
        "index.html",
        crises=crises,
        selected_range=range_key
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        region = request.form.get("region", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        source_url = request.form.get("source_url", "").strip()

        if not title or not region or not category or not description:
            return "All required fields must be filled.", 400

        current_time = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

        crisis = Crisis(
            title=title,
            region=region,
            category=category,
            description=description,
            source_url=source_url or None,
            published_at=current_time
        )

        db.session.add(crisis)
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("report.html")


@app.route("/api/crises")
def api_crises():
    crises = Crisis.query.order_by(
        Crisis.published_at.desc(),
        Crisis.created_at.desc()
    ).all()

    return [
        {
            "id": crisis.id,
            "title": crisis.title,
            "region": crisis.region,
            "category": crisis.category,
            "description": crisis.description,
            "source_url": crisis.source_url,
            "published_at": (
                crisis.published_at.isoformat()
                if crisis.published_at
                else None
            ),
            "created_at": (
                crisis.created_at.isoformat()
                if crisis.created_at
                else None
            )
        }
        for crisis in crises
    ]


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
