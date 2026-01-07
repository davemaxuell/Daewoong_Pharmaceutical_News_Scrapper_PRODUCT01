# Monitor Pipeline
# Checks for updates in ICH and other sources, and analyzes them using AI

import sys
import json
import os
from datetime import datetime
from ich_monitor import ICHGuidelinesMonitor
from ai_summarizer_gemini import get_gemini_client, analyze_pdf

def run_monitor_pipeline():
    print("=" * 60)
    print("MONITOR PIPELINE START")
    print("=" * 60)
    
    today = datetime.now().strftime('%Y%m%d')
    output_file = f"monitor_updates_{today}.json"
    
    updates = []
    
    # Initialize AI
    try:
        model = get_gemini_client()
        print("[INFO] AI Model initialized (Gemini)")
    except Exception as e:
        print(f"[ERROR] AI init failed: {e}")
        model = None

    # 1. ICH Guidelines Monitor
    print("\n[1] Checking ICH Guidelines...")
    ich_monitor = ICHGuidelinesMonitor()
    ich_results = ich_monitor.check_all()
    
    for res in ich_results:
        if res.get("has_changes") and res.get("new_links"):
            print(f"  -> Found updates in {res['category']}")
            
            for link in res["new_links"]:
                # Only check PDFs
                if link.lower().endswith('.pdf'):
                    print(f"    -> Analyzing PDF: {link}")
                    
                    if model:
                        analysis = analyze_pdf(model, link, title=f"ICH {res['category']} Guideline Update")
                        
                        updates.append({
                            "source": "ICH Guidelines",
                            "category": res['category'],
                            "type": "PDF Update",
                            "link": link,
                            "ai_analysis": analysis,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        updates.append({
                            "source": "ICH Guidelines",
                            "category": res['category'],
                            "type": "PDF Update",
                            "link": link,
                            "note": "AI Analysis Skipped (No Model)",
                            "timestamp": datetime.now().isoformat()
                        })
    
    # 2. PMDA Newsletter Monitor (Quarterly)
    print("\n[2] Checking PMDA Newsletter...")
    try:
        from scrapers.pmda_scraper import PMDAScraper
        pmda = PMDAScraper()
        pmda_articles = pmda.fetch_news(days_back=90)  # 분기별 (90일)
        
        if pmda_articles:
            print(f"  -> Found {len(pmda_articles)} PMDA updates")
            for article in pmda_articles[:5]:  # 최대 5개
                update = {
                    "source": "PMDA Newsletter",
                    "title": article.title,
                    "link": article.link,
                    "published": article.published.isoformat() if article.published else None,
                    "timestamp": datetime.now().isoformat()
                }
                
                # PDF 분석 시도
                if model and article.link.lower().endswith('.pdf'):
                    print(f"    -> Analyzing: {article.title[:50]}...")
                    analysis = analyze_pdf(model, article.link, title=article.title)
                    update["ai_analysis"] = analysis
                
                updates.append(update)
        else:
            print("  -> No new PMDA updates")
    except Exception as e:
        print(f"  -> PMDA check error: {e}")
    
    # 2. Save Results
    if updates:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] Saved {len(updates)} updates to {output_file}")
    else:
        print("\n[INFO] No significant updates found in monitors.")
        # Create empty list file to indicate run happened
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_monitor_pipeline()
