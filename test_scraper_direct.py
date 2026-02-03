# Direct test of the scraper logic
import sys
sys.path.insert(0, 'src')

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

url = "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

print(f"[TEST] Fetching: {url}")
response = requests.get(url, headers=headers, timeout=30)
print(f"[TEST] Status: {response.status_code}")

soup = BeautifulSoup(response.content, 'html.parser')

# Try the exact same selector as the scraper
table = soup.find('table', class_='lcds-datatable')
print(f"[TEST] Found table with lcds-datatable: {table is not None}")

if table:
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"[TEST] Found {len(rows)} rows in tbody")
    else:
        rows = table.find_all('tr')[1:]
        print(f"[TEST] No tbody, found {len(rows)} rows")
    
    cutoff_date = datetime.now() - timedelta(days=60)
    print(f"[TEST] Cutoff date: {cutoff_date}")
    
    articles = []
    for row in rows:
        cells = row.find_all('td')
        print(f"\n[TEST] Row has {len(cells)} cells")
        
        if len(cells) < 4:
            print("[TEST] Skipping - less than 4 cells")
            continue
        
        posted_date_str = cells[0].get_text(strip=True)
        issue_date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        company = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        issuing_office = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        subject = cells[4].get_text(strip=True) if len(cells) > 4 else ""
        
        print(f"[TEST] Posted: {posted_date_str}, Issue: {issue_date_str}")
        print(f"[TEST] Company: {company}, Office: {issuing_office}")
        
        # Link extraction
        link_elem = cells[2].find('a') if len(cells) > 2 else None
        if not link_elem:
            for cell in cells:
                link_elem = cell.find('a')
                if link_elem:
                    break
        
        if not link_elem:
            print("[TEST] No link found - SKIPPING")
            continue
        
        link = link_elem.get('href', '')
        print(f"[TEST] Link: {link[:60]}...")
        
        # Date parsing
        date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"]
        published = None
        for fmt in date_formats:
            try:
                published = datetime.strptime(issue_date_str.strip(), fmt)
                print(f"[TEST] Parsed date: {published}")
                break
            except ValueError:
                pass
        
        if not published:
            for fmt in date_formats:
                try:
                    published = datetime.strptime(posted_date_str.strip(), fmt)
                    print(f"[TEST] Parsed from posted date: {published}")
                    break
                except ValueError:
                    pass
        
        if published and published < cutoff_date:
            print(f"[TEST] Date {published} is before cutoff {cutoff_date} - SKIPPING")
            continue
        
        print(f"[TEST] Article PASSED all filters!")
        articles.append(company)
    
    print(f"\n[TEST] Total articles collected: {len(articles)}")
    for a in articles[:5]:
        print(f"  - {a}")
