import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import re
import time
import random

# Your bot token here
BOT_TOKEN = "8234150234:AAFy9UM0zsu1XgYEfZV-xv0ABEK8YaK9Qbs"


# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# A list of common User-Agents to rotate through. This helps avoid being blocked.
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
]

# --- Helper functions to scrape different portals ---

def get_headers():
    """Returns a random User-Agent header for each request."""
    return {'User-Agent': random.choice(USER_AGENTS)}

def scrape_internshala(query):
    """Scrapes internships from Internshala."""
    jobs = []
    try:
        url = f"https://internshala.com/internships/keywords-{query.replace(' ', '-')}/"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        internships = soup.find_all('div', class_='individual_internship')
        for internship in internships:
            try:
                title_tag = internship.find('div', class_='heading_4_5')
                if not title_tag:
                    continue
                title = title_tag.text.strip()
                link = "https://internshala.com" + title_tag.find('a')['href']
                company = internship.find('a', class_='link_display_like_text').text.strip()
                location = internship.find('a', class_='location_link').text.strip() if internship.find('a', class_='location_link') else 'N/A'
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Source": "Internshala"})
            except Exception as e:
                logging.error(f"Error parsing Internshala internship: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape Internshala: {e}")
    return jobs

def scrape_cutshort(query):
    """Scrapes jobs from Cutshort.io."""
    jobs = []
    try:
        url = f"https://cutshort.io/jobs/{query.replace(' ', '-')}-jobs"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all('div', class_='job_listing_title__text')
        for card in job_cards[:10]:
            try:
                title = card.text.strip()
                link = "https://cutshort.io" + card.find_parent('a')['href']
                jobs.append({"Title": title, "Company": "N/A", "Location": "N/A", "Link": link, "Source": "Cutshort"})
            except Exception as e:
                logging.error(f"Error parsing Cutshort job: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape Cutshort: {e}")
    return jobs

def scrape_indeed(query, location="India"):
    """Scrapes jobs from Indeed. Includes a random delay."""
    jobs = []
    try:
        url = f"https://in.indeed.com/jobs?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        for card in job_cards[:10]:
            try:
                title_tag = card.find('h2', class_='jobTitle')
                title = title_tag.find('span').text.strip() if title_tag and title_tag.find('span') else 'N/A'
                link = "https://in.indeed.com" + title_tag.find('a')['href'] if title_tag and title_tag.find('a') else 'N/A'
                company = card.find('span', class_='companyName').text.strip() if card.find('span', class_='companyName') else 'N/A'
                location = card.find('div', class_='companyLocation').text.strip() if card.find('div', class_='companyLocation') else 'N/A'
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Source": "Indeed"})
            except Exception as e:
                logging.error(f"Error parsing Indeed job: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape Indeed: {e}")
    return jobs

def scrape_naukri(query):
    """
    Scrapes jobs from Naukri.com.
    NOTE: Naukri.com is highly dynamic. The selectors here may need frequent updates.
    A more reliable solution would involve a headless browser like Selenium or Playwright.
    """
    jobs = []
    try:
        # Note: Naukri's URL structure is complex. We'll use a basic search URL.
        url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        job_cards = soup.find_all('div', class_='jobTupleHeader')
        for card in job_cards[:10]:
            try:
                title_tag = card.find('a', class_='title')
                title = title_tag.text.strip() if title_tag else 'N/A'
                link = title_tag['href'] if title_tag else 'N/A'
                company = card.find('a', class_='subTitle').text.strip() if card.find('a', class_='subTitle') else 'N/A'
                location = card.find('span', class_='ellipsis').text.strip() if card.find('span', class_='ellipsis') else 'N/A'
                
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Source": "Naukri"})
            except Exception as e:
                logging.error(f"Error parsing Naukri job: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape Naukri: {e}")
    return jobs

def scrape_linkedin(query):
    """
    Scrapes jobs from LinkedIn.
    WARNING: LinkedIn is highly protected against scraping. This is for demonstration.
    A simple requests-based scraper is likely to be blocked very quickly.
    You would need a more advanced setup with sessions, cookies, or a headless browser.
    """
    jobs = []
    try:
        url = f"https://www.linkedin.com/jobs/search?keywords={query.replace(' ', '%20')}"
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        job_cards = soup.find_all('div', class_='base-card')
        for card in job_cards[:10]:
            try:
                title = card.find('h3', class_='base-search-card__title').text.strip()
                company = card.find('h4', class_='base-search-card__subtitle').text.strip()
                location = card.find('span', class_='job-search-card__location').text.strip()
                link = card.find('a', class_='base-card__full-link')['href']
                
                jobs.append({"Title": title, "Company": company, "Location": location, "Link": link, "Source": "LinkedIn"})
            except Exception as e:
                logging.error(f"Error parsing LinkedIn job: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape LinkedIn: {e}")
    return jobs


# --- Main Bot Logic ---

def search_jobs(query):
    """
    Combines jobs from all sources.
    Adds random delays between each scraper to reduce the risk of being blocked.
    """
    all_jobs = []
    
    logging.info(f"Scraping Internshala for '{query}'...")
    all_jobs.extend(scrape_internshala(query))
    time.sleep(random.uniform(2, 5)) 
    
    logging.info(f"Scraping Cutshort for '{query}'...")
    all_jobs.extend(scrape_cutshort(query))
    time.sleep(random.uniform(2, 5))
    
    logging.info(f"Scraping Indeed for '{query}'...")
    all_jobs.extend(scrape_indeed(query))
    time.sleep(random.uniform(2, 5))
    
    logging.info(f"Scraping Naukri for '{query}'...")
    all_jobs.extend(scrape_naukri(query))
    time.sleep(random.uniform(2, 5))
    
    logging.info(f"Scraping LinkedIn for '{query}'...")
    all_jobs.extend(scrape_linkedin(query))
    
    return all_jobs

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and explains how to use the bot."""
    await update.message.reply_text(
        "👋 Hello! I can help you search for jobs across multiple portals.\n\n"
        "Just send me a job keyword like:\n"
        "`python developer` or `data scientist remote`\n\n"
        "I'll find the jobs and send you a CSV file with all the details!"
    )

# Handle keyword messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the user's job search query and sends a CSV file."""
    query = update.message.text.strip().lower()
    await update.message.reply_text(f"🔍 Searching for jobs with keyword: `{query}`. Please wait...", parse_mode="Markdown")

    job_list = search_jobs(query)
    
    if not job_list:
        await update.message.reply_text("❌ No jobs found. Try a different keyword.")
        return

    df = pd.DataFrame(job_list)
    
    # Remove duplicates based on Title and Company to get cleaner results
    df.drop_duplicates(subset=['Title', 'Company'], inplace=True)
    
    file_path = f"{query.replace(' ', '_')}_job_results.csv"
    df.to_csv(file_path, index=False)

    await update.message.reply_document(
        document=open(file_path, "rb"),
        filename=file_path,
        caption=f"✅ Found {len(df)} jobs for '{query}'."
    )

# Main function
if __name__ == "__main__":
    # Ensure you've replaced the placeholder BOT_TOKEN with your actual token
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        raise ValueError("Please replace 'YOUR_TELEGRAM_BOT_TOKEN_HERE' with your actual bot token.")
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers for different commands and messages
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running... Press Ctrl+C to stop.")
    app.run_polling()