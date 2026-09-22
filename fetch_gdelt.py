import time

import requests


URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt():
    params = {
        "query": "flood",
        "mode": "artlist",
        "format": "json",
        "maxrecords": 3,
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

        for article in articles:
            print("\nTITLE:", article.get("title"))
            print("URL:", article.get("url"))
            print("DATE:", article.get("seendate"))

    except requests.RequestException as error:
        print("Connection error:", error)


if __name__ == "__main__":
    fetch_gdelt()