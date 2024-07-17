# Subreddit Message Scraper

This script scrapes URLs from all messages (both submissions and comments) in a specific subreddit from now until a specified date. The URLs are filtered based on allowed domains and stored in a local SQLite database.

## Commands to run:

```bash
python -m venv venv

./venv/Scripts/activate

pip install flask requests pdraw bs4

python script.py

``` 

### Post Request to scrape

```bash
curl -X POST http://localhost:5000/scrape_subreddit \
    -H "Content-Type: application/json" \
    -d '{"subreddit": "YourSubreddit", "end_date": "2024-07-01"}' can change date to anything
```
