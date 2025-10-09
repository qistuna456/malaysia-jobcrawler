# Malaysia Remote Job Crawler (Improved - Fixed Indeed selectors)

import time
import random
import csv
import re
import sys
import traceback

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================ CONFIG ============================
KEYWORDS = [
    "Full-Stack Developer",
    "Backend Developer",
    "Application Analyst",
    "Systems Analyst",
    "ERP Consultant",
    "ERP Developer",
    "Technical Support Lead",
    "IT Support Specialist",
    "Data Analyst",
    "BI Analyst",
    "DevOps",
    "System Engineer",
    "Agile Project Coordinator",
    "Junior Project Manager",
    "Mobile App Developer",
    "Flutter"
]

MAX_PAGES = 3
OUTPUT_FILE = "malaysia_remote_jobs.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ============================ SELENIUM SETUP ============================
def make_selenium_driver():
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print("[ERROR] Selenium driver init failed:", e)
        return None

# ============================ HELPER ============================
def safe_get_text(el):
    return el.get_text(strip=True) if el else ""

def handle_error(site_name, e):
    print(f"[WARNING] {site_name} - {str(e)}")
    traceback.print_exc(limit=1)

# ============================ SCRAPER FUNCTIONS ============================

def scrape_indeed():
    jobs = []
    base_url = "https://my.indeed.com/jobs?q=remote&l=Malaysia"
    driver = make_selenium_driver()
    if not driver:
        return jobs
    try:
        for page in range(0, MAX_PAGES):
            url = f"{base_url}&start={page * 10}"
            print(f"[INFO] Indeed -> {url}")
            driver.get(url)

            # Tunggu sehingga job list dimuat
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.jcs-JobTitle"))
                )
            except:
                print("[WARNING] No job elements found on page")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            for card in soup.select("a.jcs-JobTitle"):
                title = safe_get_text(card)
                link = card.get("href")
                if not link or not title:
                    continue

                # Find parent container to extract company/location
                parent = card.find_parent("td")
                company_el = parent.find_next("span", class_="companyName") if parent else None
                location_el = parent.find_next("div", class_="companyLocation") if parent else None

                if not any(k.lower() in title.lower() for k in KEYWORDS):
                    continue

                jobs.append({
                    "site": "Indeed",
                    "title": title,
                    "company": safe_get_text(company_el),
                    "location": safe_get_text(location_el),
                    "url": f"https://my.indeed.com{link}"
                })
            time.sleep(random.uniform(1, 3))
    except Exception as e:
        handle_error("Indeed", e)
    finally:
        driver.quit()
    return jobs


def scrape_maukerja():
    jobs = []
    try:
        for page in range(1, MAX_PAGES + 1):
            url = f"https://www.maukerja.my/jobs?keyword=remote&page={page}"
            print(f"[INFO] Maukerja -> {url}")
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            # Debug jika tiada hasil
            cards = soup.select("div.job-card")
            if not cards:
                print("[WARNING] No job-card found on Maukerja page", page)

            for card in cards:
                title_el = card.select_one("h3")
                company_el = card.select_one("p.company")
                link_el = card.find("a", href=True)
                if not title_el or not link_el:
                    continue
                title = safe_get_text(title_el)
                if not any(k.lower() in title.lower() for k in KEYWORDS):
                    continue
                jobs.append({
                    "site": "Maukerja",
                    "title": title,
                    "company": safe_get_text(company_el),
                    "location": "Remote",
                    "url": link_el["href"]
                })
            time.sleep(random.uniform(1, 2))
    except Exception as e:
        handle_error("Maukerja", e)
    return jobs

# Placeholder stubs for other sites to avoid spamming warnings
def scrape_placeholder(site_name):
    print(f"[INFO] Skipping {site_name} (not implemented yet)")
    return []

# ============================ MAIN ============================
ALL_SITES = [
    scrape_indeed,
    scrape_maukerja,
    lambda: scrape_placeholder("JobStreet"),
    lambda: scrape_placeholder("LinkedIn"),
    lambda: scrape_placeholder("MyFutureJobs"),
    lambda: scrape_placeholder("Hiredly"),
    lambda: scrape_placeholder("FastJobs"),
    lambda: scrape_placeholder("Glassdoor"),
    lambda: scrape_placeholder("FoundIt"),
    lambda: scrape_placeholder("Tech in Asia"),
]

def save_to_csv(jobs):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site","title","company","location","url"])
        writer.writeheader()
        for j in jobs:
            writer.writerow(j)


def main():
    all_jobs = []
    for scraper in ALL_SITES:
        try:
            jobs = scraper()
            print(f"[INFO] {len(jobs)} jobs scraped.")
            all_jobs.extend(jobs)
        except Exception as e:
            handle_error(scraper.__name__, e)
    print(f"[DONE] Total jobs scraped: {len(all_jobs)}")
    save_to_csv(all_jobs)

if __name__ == "__main__":
    main()
