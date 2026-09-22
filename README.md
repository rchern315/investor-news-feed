Central Garden & Pet — Investor News Alerts

Published RSS feed:
https://rchern315.github.io/investor-news-feed/news-feed.xml

This repository powers an automated investor news alert system for Central Garden & Pet (CENTA / CENT). It aggregates the latest company-related news using public Yahoo Finance and Google News RSS sources and publishes it as a clean, standardized RSS feed.

The project is built with Python, configured via YAML, and kept up to date automatically through GitHub Actions.

What This Project Does

📈 Collects the latest investor and market news for CENTA / CENT

🔄 Normalizes external RSS sources into a single, consistent feed

🤖 Runs on a scheduled basis using GitHub Actions

📝 Commits updates only when new content is detected

The generated feed is written to:

docs/news-feed.xml

GitHub Pages publishes that file at:

https://rchern315.github.io/investor-news-feed/news-feed.xml

Tech Stack

Python 3.12

PyYAML

Requests

GitHub Actions

RSS (XML)
