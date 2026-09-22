import requests

from app import app, db, Crisis


URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt():
    params = {
        "query": "flood OR earthquake OR wildfire OR cyclone",
        "mode": "artlist",
        "format": "json",
        "maxrecords": 5,
        "timespan": "1h",
    }

    try:
        response = requests.get(URL, params=params, timeout=60)

        print("Status:", response.status_code)

        if response.status_code == 429:
            print("GDELT rate limit reached.")
            print("Please wait before trying again.")
            return

        if response.status_code != 200:
            print("GDELT request failed.")
            print(response.text[:500])
            return

        content_type = response.headers.get("content-type", "")

        if "json" not in content_type.lower():
            print("GDELT did not return JSON.")
            print(response.text[:500])
            return

        data = response.json()
        articles = data.get("articles", [])

        print("Articles found:", len(articles))

        with app.app_context():
            for article in articles:
                title = article.get("title", "").strip()
                source_url = article.get("url", "").strip()

                if not title or not source_url:
                    continue

                existing = Crisis.query.filter_by(
                    source_url=source_url
                ).first()

                if existing:
                    print("Already exists:", title)
                    continue

                crisis = Crisis(
                    title=title,
                    region="Global",
                    category="External News",
                    description=(
                        "Automatically collected crisis-related "
                        "news from GDELT."
                    ),
                    source_url=source_url,
                )

                db.session.add(crisis)

            db.session.commit()

        print("New articles saved to CrisisLens.")

    except requests.RequestException as error:
        print("Connection error:", error)


if __name__ == "__main__":
    fetch_gdelt()