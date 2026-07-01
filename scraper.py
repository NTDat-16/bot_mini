from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://support.optisigns.com"
ARTICLES_API_URL = f"{BASE_URL}/api/v2/help_center/en-us/articles.json"
DEFAULT_TIMEOUT = 20
HEADERS = {
    "User-Agent": "OptiSignsDocsBot/1.0 (+https://support.optisigns.com)"
}


def _normalize_url(href):
    url = urljoin(BASE_URL, href)
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def fetch_articles(limit=30):
    articles = []
    next_page = f"{ARTICLES_API_URL}?per_page=100"

    while next_page and (not limit or len(articles) < limit):
        response = requests.get(next_page, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()

        for article in payload.get("articles", []):
            if article.get("draft"):
                continue

            articles.append(
                {
                    "title": article["title"],
                    "url": article["html_url"],
                    "html": article.get("body") or "",
                    "updated_at": article.get("updated_at"),
                }
            )
            if limit and len(articles) >= limit:
                break

        next_page = payload.get("next_page")

    return articles


def get_article_links(limit=30):
    try:
        return [article["url"] for article in fetch_articles(limit=limit)]
    except requests.RequestException:
        pass

    response = requests.get(BASE_URL, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = _normalize_url(a["href"])
        if "/hc/en-us/articles/" not in href or href in seen:
            continue

        seen.add(href)
        links.append(href)
        if limit and len(links) >= limit:
            break

    return links


def scrape_article(url):
    response = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.find("h1")
    body = soup.find("article")

    if title_tag is None:
        raise ValueError(f"Could not find article title for {url}")
    if body is None:
        raise ValueError(f"Could not find article body for {url}")

    title = title_tag.get_text(strip=True)
    body_title = body.find("h1")
    if body_title:
        body_title.decompose()

    return title, str(body)
