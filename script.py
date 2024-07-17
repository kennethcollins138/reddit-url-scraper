from flask import Flask, request, redirect, jsonify
import praw
import json
from bs4 import BeautifulSoup
import re
import time
import logging
from datetime import datetime, timezone
import sqlite3

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = get_config()

app = Flask(__name__)
app.secret_key = config['secret']

reddit = praw.Reddit(client_id=config['client_id'],
                     client_secret=config['client_secret'],
                     user_agent=config['user_agent'],
                     redirect_uri=config['redirect_uri'])

def init_db():
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            submission_title TEXT,
            submission_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def store_links_in_db(links, submission_title, submission_date):
    conn = sqlite3.connect('links.db')
    cursor = conn.cursor()
    for link in links:
        cursor.execute('''
            INSERT INTO links (url, submission_title, submission_date)
            VALUES (?, ?, ?)
        ''', (link, submission_title, submission_date))
    conn.commit()
    conn.close()

def match_pattern(link, patterns):
    return any(re.search(pattern, link) for pattern in patterns)

def extract_links(text, patterns):
    soup = BeautifulSoup(text, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    filtered_links = [link for link in links if match_pattern(link, patterns)]
    return filtered_links

@app.route('/')
def home():
    auth_url = reddit.auth.url(scopes=['identity', 'read'], state='uniqueKey', duration='permanent')
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    reddit.auth.authorize(code)
    return "Authorization successful! Use the /scrape_subreddit endpoint with a subreddit name and end date."

@app.route('/scrape_subreddit', methods=['POST'])
def scrape_subreddit():
    data = request.json
    subreddit_name = data.get('subreddit')
    end_date_str = data.get('end_date')
    if not subreddit_name or not end_date_str:
        return jsonify({"error": "Missing 'subreddit' or 'end_date' parameter"}), 400
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    
    allowed_domains = config['allowed_domains']
    all_links = []
    
    try:
        logger.info(f"Starting to scrape subreddit: {subreddit_name}")
        subreddit = reddit.subreddit(subreddit_name)
        for submission in subreddit.new(limit=None):
            submission_date = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if submission_date < end_date:
                break
            links = extract_links(submission.selftext_html or submission.selftext, allowed_domains)
            all_links.extend(links)
            store_links_in_db(links, submission.title, submission_date.isoformat())
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                links = extract_links(comment.body_html or comment.body, allowed_domains)
                all_links.extend(links)
                store_links_in_db(links, submission.title, submission_date.isoformat())
            time.sleep(0.7)  # Test this val, api is 100 queries per min

        logger.info("Scraping completed successfully.")
        return jsonify(all_links)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    init_db()
    app.run(port=5000)
