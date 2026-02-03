# Monitor Pipeline
# Checks for updates in ICH, PMDA, USP and other sources, and analyzes them using AI

import sys
import json
import os
from datetime import datetime

# 프로젝트 루트 설정 (src/ 상위 디렉토리)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.ich_monitor import ICHGuidelinesMonitor
from src.ai_summarizer_gemini import get_gemini_client, analyze_pdf

# config 디렉토리에서 .env 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))

# Snapshot directory for change detection
SNAPSHOT_DIR_USP = os.path.join(PROJECT_ROOT, "snapshots", "usp")
SNAPSHOT_DIR_PMDA = os.path.join(PROJECT_ROOT, "snapshots", "pmda")
DATA_MONITORS_DIR = os.path.join(PROJECT_ROOT, "data", "monitors")

def load_usp_snapshot():
    """Load previous USP PDF links snapshot"""
    snapshot_file = os.path.join(SNAPSHOT_DIR_USP, "usp_pdfs.json")
    if os.path.exists(snapshot_file):
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_usp_snapshot(pdf_links):
    """Save current USP PDF links snapshot"""
    os.makedirs(SNAPSHOT_DIR_USP, exist_ok=True)
    snapshot_file = os.path.join(SNAPSHOT_DIR_USP, "usp_pdfs.json")
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(list(pdf_links), f, ensure_ascii=False, indent=2)

def load_pmda_snapshot():
    """Load previous PMDA PDF links snapshot"""
    snapshot_file = os.path.join(SNAPSHOT_DIR_PMDA, "pmda_pdfs.json")
    if os.path.exists(snapshot_file):
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_pmda_snapshot(pdf_links):
    """Save current PMDA PDF links snapshot"""
    os.makedirs(SNAPSHOT_DIR_PMDA, exist_ok=True)
    snapshot_file = os.path.join(SNAPSHOT_DIR_PMDA, "pmda_pdfs.json")
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(list(pdf_links), f, ensure_ascii=False, indent=2)

def run_monitor_pipeline():
    print("=" * 60)
    print("MONITOR PIPELINE START")
    print("=" * 60)
    
    # Ensure output directory exists
    os.makedirs(DATA_MONITORS_DIR, exist_ok=True)
    
    today = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(DATA_MONITORS_DIR, f"monitor_updates_{today}.json")
    
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
    
    # 2. PMDA Newsletter Monitor (with Change Detection)
    print("\n[2] Checking PMDA Newsletter...")
    try:
        from scrapers.pmda_scraper import PMDAScraper
        pmda = PMDAScraper()
        
        # Load previous snapshot
        previous_pmda_pdfs = load_pmda_snapshot()
        
        # Fetch current PMDA articles (only 2 most recent)
        pmda_articles = pmda.fetch_news(days_back=365, max_pdfs=2)
        
        if pmda_articles:
            # Get all current PDF links
            current_pmda_pdfs = set(article.link for article in pmda_articles)
            
            # Find NEW PDFs (not in previous snapshot)
            new_pmda_pdfs = current_pmda_pdfs - previous_pmda_pdfs
            
            if new_pmda_pdfs:
                print(f"  -> Found {len(new_pmda_pdfs)} NEW PMDA updates (out of {len(pmda_articles)} total)")
                
                # Only process new articles
                for article in pmda_articles:
                    if article.link in new_pmda_pdfs:
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
                
                # Save updated snapshot
                save_pmda_snapshot(current_pmda_pdfs)
            else:
                print(f"  -> No NEW PMDA updates (already seen {len(current_pmda_pdfs)} PDFs)")
                # Still update snapshot in case of first run
                if not previous_pmda_pdfs:
                    save_pmda_snapshot(current_pmda_pdfs)
                    print(f"  -> Initialized PMDA snapshot with {len(current_pmda_pdfs)} PDFs")
        else:
            print("  -> No PMDA updates found")
    except Exception as e:
        print(f"  -> PMDA check error: {e}")
    
    # 3. USP Pending Monographs Monitor (Change Detection)
    print("\n[3] Checking USP Pending Monographs...")
    try:
        from scrapers.usp_monograph_scraper import USPMonographScraper
        usp = USPMonographScraper()
        
        # Load previous snapshot
        previous_pdfs = load_usp_snapshot()
        
        # Fetch current USP articles (use longer lookback for change detection)
        usp_articles = usp.fetch_news(days_back=30)
        
        # Extract current PDF links
        current_pdfs = set()
        for article in usp_articles:
            if article.link:
                current_pdfs.add(article.link)
        
        # Find new PDFs (not in previous snapshot)
        new_pdfs = current_pdfs - previous_pdfs
        
        if new_pdfs:
            print(f"  -> Found {len(new_pdfs)} NEW USP updates!")
            
            for article in usp_articles:
                if article.link in new_pdfs:
                    update = {
                        "source": "USP Pending Monographs",
                        "title": article.title,
                        "link": article.link,
                        "published": article.published.isoformat() if article.published else None,
                        "type": "New Monograph/Revision",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Analyze PDF if model available
                    if model and article.link.lower().endswith('.pdf'):
                        print(f"    -> Analyzing: {article.title[:50]}...")
                        try:
                            analysis = analyze_pdf(model, article.link, title=article.title)
                            update["ai_analysis"] = analysis
                        except Exception as e:
                            print(f"    -> PDF analysis failed: {e}")
                            update["ai_analysis"] = {"error": str(e)}
                    
                    updates.append(update)
            
            # Update snapshot with all current PDFs
            save_usp_snapshot(current_pdfs)
            print(f"  -> Updated USP snapshot with {len(current_pdfs)} PDFs")
        else:
            print(f"  -> No new USP updates (tracking {len(current_pdfs)} PDFs)")
            # Still update snapshot in case some were removed
            if current_pdfs:
                save_usp_snapshot(current_pdfs)
                
    except ImportError:
        print("  -> USP scraper not available (missing dependencies)")
    except Exception as e:
        print(f"  -> USP check error: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Save Results
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
