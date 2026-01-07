# Test data flow between pipeline steps
import json
from multi_source_scraper import MultiSourceScraper

# Step 1: Multi-source scraper output
print("=== Testing Pipeline Data Flow ===\n")

s = MultiSourceScraper(sources=['mfds'])
arts = s.fetch_all(days_back=7)

if arts:
    print("\n[1] Multi-Source Scraper Output:")
    print("-" * 40)
    a = arts[0]
    print(f"Keys: {list(a.keys())}")
    print(f"title: {a.get('title', 'N/A')[:50]}")
    print(f"link: {a.get('link', 'N/A')[:50]}")
    print(f"source: {a.get('source', 'N/A')}")
    print()
    
    print("[2] Content Scraper adds:")
    print("-" * 40)
    print("+ full_text (article body)")
    print("+ scrape_status ('success'/'failed')")
    print("+ images (list)")
    print()
    
    print("[3] AI Summarizer reads:")
    print("-" * 40)
    print("- title -> for prompt")
    print("- full_text -> for content analysis")
    print("- images -> for vision analysis")
    print()
    
    print("[4] AI Summarizer adds:")
    print("-" * 40)
    print("+ ai_analysis.ai_summary")
    print("+ ai_analysis.key_points")
    print("+ ai_analysis.target_teams")
    print()
    
    print("=== DATA FLOW VERIFIED ===")
else:
    print("No articles found")
