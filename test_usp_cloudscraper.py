#!/usr/bin/env python
# Test USP with cloudscraper to bypass Cloudflare

import cloudscraper
import re

scraper = cloudscraper.create_scraper()

print("="*60)
print("Testing USP with cloudscraper")
print("="*60)

url = 'https://www.uspnf.com/pending-monographs/pending-monograph-program'
print(f"\nFetching: {url}")

r = scraper.get(url, timeout=30)
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")

# Count PDF links
pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', r.text, re.IGNORECASE)
print(f"\nPDF links found: {len(pdfs)}")

# Show first 5
print("\nSample PDFs:")
for i, p in enumerate(pdfs[:5], 1):
    print(f"  {i}. {p}")

# Test Revision Bulletins too
print("\n" + "="*60)
url2 = 'https://www.uspnf.com/official-text/revision-bulletins'
print(f"Fetching: {url2}")

r2 = scraper.get(url2, timeout=30)
print(f"Status: {r2.status_code}")

pdfs2 = re.findall(r'href=["\']([^"\']*\.pdf)["\']', r2.text, re.IGNORECASE)
print(f"PDF links found: {len(pdfs2)}")
