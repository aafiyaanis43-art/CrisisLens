import pytest

from app import app, db, Crisis


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_add_crisis(client):
    response = client.post(
        "/report",
        data={
            "title": "Test earthquake",
            "region": "South Asia",
            "category": "Natural Disaster",
            "description": "Test crisis report",
            "source_url": "",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        crisis = Crisis.query.filter_by(
            title="Test earthquake"
        ).first()

        assert crisis is not None
        assert crisis.region == "South Asia"
        assert crisis.category == "Natural Disaster"


def test_invalid_crisis_rejected(client):
    response = client.post(
        "/report",
        data={
            "title": "",
            "region": "South Asia",
            "category": "Natural Disaster",
            "description": "Test crisis report",
            "source_url": "",
        },
    )

    assert response.status_code == 400
