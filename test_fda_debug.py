# Debug FDA scraper
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

url = "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=30)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.content, 'html.parser')

# Try different table selectors
table = soup.find('table', class_='lcds-datatable')
if not table:
    table = soup.find('table', class_='views-table')
if not table:
    table = soup.find('table', class_='usa-table')
if not table:
    table = soup.find('table')

if table:
    print(f"\nTable found: class={table.get('class')}")
    
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"Using tbody, found {len(rows)} rows")
    else:
        rows = table.find_all('tr')[1:]  # Skip header
        print(f"No tbody, found {len(rows)} rows (excluding header)")
    
    cutoff = datetime.now() - timedelta(days=60)
    print(f"Cutoff date: {cutoff}")
    
    for i, row in enumerate(rows[:5]):
        cells = row.find_all('td')
        print(f"\nRow {i}: {len(cells)} cells")
        
        if len(cells) >= 4:
            posted = cells[0].get_text(strip=True)
            issue = cells[1].get_text(strip=True)
            company = cells[2].get_text(strip=True)
            office = cells[3].get_text(strip=True)
            
            print(f"  Posted: {posted}")
            print(f"  Issue Date: {issue}")
            print(f"  Company: {company}")
            print(f"  Office: {office}")
            
            # Try to parse date
            for fmt in ["%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(issue, fmt)
                    print(f"  Parsed date: {dt}")
                    print(f"  After cutoff? {dt >= cutoff}")
                    break
                except:
                    pass
            
            # Check link
            link_elem = cells[2].find('a')
            if link_elem:
                print(f"  Link: {link_elem.get('href', 'NO HREF')[:80]}")
            else:
                print(f"  Link: NOT FOUND in cell 2")
else:
    print("No table found!")
