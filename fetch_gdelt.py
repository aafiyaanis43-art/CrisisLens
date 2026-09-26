import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from app import app, db, Crisis


RSS_URL = "https://data.gdeltproject.org/gdeltv3/gal/feed.rss"


ENGLISH_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "in",
    "on",
    "at",
    "after",
    "before",
    "near",
    "over",
    "under",
    "hits",
    "hit",
    "strikes",
    "strike",
    "killed",
    "dead",
    "injured",
    "reported",
    "reports",
    "warning",
    "warnings",
    "officials",
    "government",
    "residents",
    "emergency",
    "crisis",
    "disaster",
    "causes",
    "caused",
    "forces",
    "fire",
    "fires",
    "people",
    "city",
    "country",
    "latest",
    "major",
}


def is_english_headline(title):
    """Conservatively keep headlines that look English."""

    # Reject obvious non-Latin scripts.
    non_latin_patterns = [
        r"[\u0600-\u06ff]",  # Arabic
        r"[\u0900-\u097f]",  # Devanagari
        r"[\u0980-\u09ff]",  # Bengali
        r"[\u0a00-\u0a7f]",  # Gurmukhi
        r"[\u0a80-\u0aff]",  # Gujarati
        r"[\u0b00-\u0b7f]",  # Odia
        r"[\u0b80-\u0bff]",  # Tamil
        r"[\u0c00-\u0c7f]",  # Telugu
        r"[\u0c80-\u0cff]",  # Kannada
        r"[\u0d00-\u0d7f]",  # Malayalam
        r"[\u0e00-\u0e7f]",  # Thai
        r"[\u3040-\u30ff]",  # Japanese
        r"[\u3400-\u9fff]",  # Chinese
        r"[\uac00-\ud7af]",  # Korean
        r"[\u0400-\u04ff]",  # Cyrillic
    ]

    for pattern in non_latin_patterns:
        if re.search(pattern, title):
            return False

    words = re.findall(r"[A-Za-z]+", title.lower())

    if not words:
        return False

    english_matches = sum(
        word in ENGLISH_WORDS
        for word in words
    )

    # Short headlines need at least one strong English indicator.
    if len(words) <= 6:
        return english_matches >= 1

    # Longer headlines need at least two.
    return english_matches >= 2


def contains_keyword(title, keywords):
    """Match complete words or phrases."""

    title = title.lower()

    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"

        if re.search(pattern, title):
            return True

    return False


def detect_category(title):
    """Classify crisis-related headlines."""

    natural_disaster = [
        "earthquake",
        "flood",
        "flooding",
        "cyclone",
        "hurricane",
        "wildfire",
        "forest fire",
        "volcano",
        "volcanic eruption",
        "tornado",
        "tsunami",
        "landslide",
        "mudslide",
        "storm",
        "severe weather",
        "extreme weather",
        "evacuation",
        "evacuations",
        "natural disaster",
    ]

    conflict = [
        "armed conflict",
        "military conflict",
        "terrorist attack",
        "terror attack",
        "missile strike",
        "airstrike",
        "air strike",
        "bombing",
        "shelling",
        "gunfire",
        "shooting",
        "fighting",
        "clashes",
        "military strike",
        "invasion",
        "war",
    ]

    health = [
        "outbreak",
        "virus outbreak",
        "disease outbreak",
        "epidemic",
        "pandemic",
        "infectious disease",
        "disease spread",
        "health emergency",
        "public health emergency",
        "cholera",
        "dengue outbreak",
        "measles outbreak",
    ]

    humanitarian = [
        "refugee",
        "refugees",
        "humanitarian crisis",
        "humanitarian aid",
        "displacement",
        "displaced",
        "famine",
        "food crisis",
        "food shortage",
        "aid emergency",
        "civilian crisis",
    ]

    if contains_keyword(title, natural_disaster):
        return "Natural Disaster"

    if contains_keyword(title, conflict):
        return "Conflict"

    if contains_keyword(title, health):
        return "Health"

    if contains_keyword(title, humanitarian):
        return "Humanitarian"

    return None


def detect_region(title):
    """Infer a broad region from the headline."""

    title = title.lower()

    regions = {
        "South Asia": [
            "india",
            "pakistan",
            "bangladesh",
            "nepal",
            "sri lanka",
            "afghanistan",
            "mumbai",
            "delhi",
            "kolkata",
            "punjab",
            "kashmir",
        ],
        "Southeast Asia": [
            "thailand",
            "bangkok",
            "indonesia",
            "jakarta",
            "philippines",
            "manila",
            "vietnam",
            "hanoi",
            "myanmar",
            "malaysia",
            "singapore",
            "cambodia",
            "laos",
        ],
        "East Asia": [
            "china",
            "beijing",
            "shanghai",
            "japan",
            "tokyo",
            "south korea",
            "korea",
            "seoul",
            "taiwan",
        ],
        "Middle East": [
            "israel",
            "palestine",
            "gaza",
            "west bank",
            "iran",
            "iraq",
            "syria",
            "lebanon",
            "yemen",
            "jordan",
            "saudi arabia",
            "uae",
            "dubai",
        ],
        "Europe": [
            "ukraine",
            "russia",
            "france",
            "germany",
            "italy",
            "spain",
            "united kingdom",
            "britain",
            "england",
            "poland",
            "greece",
            "romania",
            "netherlands",
            "sweden",
            "norway",
        ],
        "North America": [
            "united states",
            "usa",
            "america",
            "canada",
            "mexico",
            "new york",
            "california",
            "florida",
            "texas",
        ],
        "Africa": [
            "nigeria",
            "kenya",
            "sudan",
            "somalia",
            "ethiopia",
            "south africa",
            "congo",
            "egypt",
            "libya",
            "morocco",
            "tunisia",
        ],
        "South America": [
            "brazil",
            "argentina",
            "chile",
            "colombia",
            "peru",
            "bolivia",
            "ecuador",
            "venezuela",
        ],
        "Oceania": [
            "australia",
            "sydney",
            "melbourne",
            "new zealand",
            "auckland",
        ],
    }

    for region, locations in regions.items():
        if contains_keyword(title, locations):
            return region

    return "Global"


def parse_gdelt_date(item):
    """Read publication time from RSS."""

    date_element = item.find("pubDate")

    if date_element is None or not date_element.text:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        return datetime.strptime(
            date_element.text.strip(),
            "%a, %d %b %Y %H:%M:%S %Z",
        )
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def fetch_gdelt():
    """Fetch recent English crisis news from GDELT."""

    try:
        response = requests.get(
            RSS_URL,
            timeout=30,
            headers={
                "User-Agent": "CrisisLens/1.0"
            },
        )

        print("Status:", response.status_code)

        if response.status_code != 200:
            print("GDELT RSS request failed.")
            print(response.text[:500])
            return

        root = ET.fromstring(response.content)

        articles = []

        for item in root.findall(".//item"):
            title_element = item.find("title")
            link_element = item.find("link")

            if (
                title_element is None
                or link_element is None
            ):
                continue

            title = (
                title_element.text or ""
            ).strip()

            source_url = (
                link_element.text or ""
            ).strip()

            if not title or not source_url:
                continue

            articles.append(
                {
                    "title": title,
                    "url": source_url,
                    "published_at": parse_gdelt_date(item),
                }
            )

        print(
            "RSS articles found:",
            len(articles)
        )

        added = 0
        skipped = 0
        non_english = 0

        with app.app_context():

            for article in articles:
                title = article["title"]
                source_url = article["url"]

                if not is_english_headline(title):
                    non_english += 1
                    skipped += 1
                    continue

                category = detect_category(title)

                if category is None:
                    skipped += 1
                    continue

                existing = Crisis.query.filter_by(
                    source_url=source_url
                ).first()

                if existing:
                    skipped += 1
                    continue

                region = detect_region(title)

                crisis = Crisis(
                    title=title,
                    region=region,
                    category=category,
                    description=(
                        "Automatically collected "
                        "crisis-related news from GDELT. "
                        "Category and region are inferred "
                        "from the article title."
                    ),
                    source_url=source_url,
                    published_at=article["published_at"],
                )

                db.session.add(crisis)
                added += 1

            db.session.commit()

        print(
            "New English crisis articles saved:",
            added
        )
        print(
            "Articles skipped:",
            skipped
        )
        print(
            "Non-English headlines skipped:",
            non_english
        )

    except ET.ParseError as error:
        print(
            "Could not parse GDELT RSS feed:",
            error
        )

    except requests.RequestException as error:
        print(
            "Connection error:",
            error
        )


if __name__ == "__main__":
    fetch_gdelt()
