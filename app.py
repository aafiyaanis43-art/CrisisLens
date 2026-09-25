from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crisislens.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Crisis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


@app.route("/")
def home():
    crises = Crisis.query.order_by(Crisis.created_at.desc()).all()
    return render_template("index.html", crises=crises)


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

        crisis = Crisis(
            title=title,
            region=region,
            category=category,
            description=description,
            source_url=source_url or None
        )

        db.session.add(crisis)
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("report.html")


@app.route("/api/crises")
def api_crises():
    crises = Crisis.query.order_by(Crisis.created_at.desc()).all()

    return [
        {
            "id": crisis.id,
            "title": crisis.title,
            "region": crisis.region,
            "category": crisis.category,
            "description": crisis.description,
            "source_url": crisis.source_url,
            "created_at": crisis.created_at.isoformat()
        }
        for crisis in crises
    ]


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True)
