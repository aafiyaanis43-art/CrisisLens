from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>CrisisLens</h1><p>Global Crisis Information & Monitoring Platform</p>"


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True)