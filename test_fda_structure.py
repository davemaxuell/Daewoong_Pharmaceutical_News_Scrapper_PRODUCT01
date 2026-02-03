# Test FDA Warning Letters page structure
import requests
from bs4 import BeautifulSoup

url = "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=30)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.content, 'html.parser')

# Find all tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables")

for i, table in enumerate(tables):
    print(f"\nTable {i}: classes={table.get('class')}")
    rows = table.find_all('tr')
    print(f"  Rows: {len(rows)}")
    if rows:
        # Show first row (header)
        first_row = rows[0]
        headers = first_row.find_all(['th', 'td'])
        print(f"  Headers: {[h.get_text(strip=True)[:30] for h in headers]}")
        
        # Show second row (first data)
        if len(rows) > 1:
            data_row = rows[1]
            cells = data_row.find_all('td')
            print(f"  First data row cells: {len(cells)}")
            for j, cell in enumerate(cells[:5]):
                text = cell.get_text(strip=True)[:50]
                link = cell.find('a')
                link_href = link.get('href', '')[:50] if link else 'NO LINK'
                print(f"    Cell {j}: {text} | Link: {link_href}")

# Also check for any data loaded via views
views = soup.find_all('div', class_='view-content')
print(f"\nFound {len(views)} view-content divs")
