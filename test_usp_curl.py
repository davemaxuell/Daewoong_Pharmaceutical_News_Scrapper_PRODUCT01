#!/usr/bin/env python
# Test USP with curl_cffi (browser impersonation)

from curl_cffi import requests
import re

print("="*60)
print("Testing USP with curl_cffi (Chrome impersonation)")
print("="*60)

url = 'https://www.uspnf.com/pending-monographs/pending-monograph-program'
print(f"\nFetching: {url}")

# Impersonate Chrome browser
r = requests.get(url, impersonate="chrome")
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")

if r.status_code == 200:
    # Count PDF links
    pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', r.text, re.IGNORECASE)
    print(f"\nPDF links found: {len(pdfs)}")

    # Show first 5
    if pdfs:
        print("\nSample PDFs:")
        for i, p in enumerate(pdfs[:5], 1):
            print(f"  {i}. ...{p[-50:]}")
else:
    print(f"\nFailed - Response: {r.text[:200]}")
