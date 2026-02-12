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
from src.eudralex_monitor import EudraLexMonitor
from src.gmpjournal_annex1_monitor import GMPJournalAnnex1Monitor
from src.ai_summarizer_gemini import get_gemini_client, analyze_pdf
import src.logger as logger

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
    monitor_results = {}  # Track results for logging

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

    ich_update_count = sum(1 for u in updates if u.get("source") == "ICH Guidelines")
    monitor_results["ICH Guidelines"] = {"status": "ok", "updates": ich_update_count}

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
            monitor_results["PMDA Newsletter"] = {"status": "ok", "updates": 0}
    except Exception as e:
        print(f"  -> PMDA check error: {e}")
        monitor_results["PMDA Newsletter"] = {"status": "error", "updates": 0, "error": str(e)}

    # Count PMDA updates if not already set
    if "PMDA Newsletter" not in monitor_results:
        pmda_count = sum(1 for u in updates if u.get("source") == "PMDA Newsletter")
        monitor_results["PMDA Newsletter"] = {"status": "ok", "updates": pmda_count}

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
                
        # Count USP updates
        usp_count = sum(1 for u in updates if u.get("source") == "USP Pending Monographs")
        monitor_results["USP Pending Monographs"] = {"status": "ok", "updates": usp_count}

    except ImportError:
        print("  -> USP scraper not available (missing dependencies)")
        monitor_results["USP Pending Monographs"] = {"status": "error", "updates": 0, "error": "missing dependencies"}
    except Exception as e:
        print(f"  -> USP check error: {e}")
        monitor_results["USP Pending Monographs"] = {"status": "error", "updates": 0, "error": str(e)}
        import traceback
        traceback.print_exc()

    # 4. EudraLex Volume 4 Monitor (EU GMP Guidelines)
    print("\n[4] Checking EudraLex Volume 4 (EU GMP)...")
    try:
        eudralex_monitor = EudraLexMonitor()
        eudralex_result = eudralex_monitor.check()

        if eudralex_result.get("has_changes"):
            print(f"  -> Changes detected: {eudralex_result.get('summary')}")

            # 새 PDF 추가
            for pdf in eudralex_result.get("new_pdfs", []):
                update = {
                    "source": "EudraLex Volume 4",
                    "type": "New/Updated GMP Document",
                    "title": pdf.get("title", "Unknown"),
                    "link": pdf.get("url", ""),
                    "timestamp": datetime.now().isoformat()
                }

                # PDF 분석
                if model and pdf.get("url", "").lower().endswith('.pdf'):
                    full_url = pdf.get("url", "")
                    if full_url.startswith('/'):
                        full_url = f"https://health.ec.europa.eu{full_url}"
                    print(f"    -> Analyzing: {pdf.get('title', '')[:50]}...")
                    try:
                        analysis = analyze_pdf(model, full_url, title=pdf.get("title", ""))
                        update["ai_analysis"] = analysis
                    except Exception as e:
                        print(f"    -> PDF analysis failed: {e}")

                updates.append(update)

            # 삭제된 PDF 기록
            for pdf in eudralex_result.get("removed_pdfs", []):
                updates.append({
                    "source": "EudraLex Volume 4",
                    "type": "Removed Document",
                    "title": pdf.get("title", "Unknown"),
                    "link": pdf.get("url", ""),
                    "timestamp": datetime.now().isoformat()
                })

        elif eudralex_result.get("status") == "first_check":
            print(f"  -> First check - baseline saved ({eudralex_result.get('pdf_count', 0)} PDFs)")
        else:
            print("  -> No changes detected")

        eudralex_count = sum(1 for u in updates if u.get("source") == "EudraLex Volume 4")
        monitor_results["EudraLex Volume 4"] = {"status": "ok", "updates": eudralex_count}

    except Exception as e:
        print(f"  -> EudraLex check error: {e}")
        monitor_results["EudraLex Volume 4"] = {"status": "error", "updates": 0, "error": str(e)}
        import traceback
        traceback.print_exc()

    # 5. GMP Journal Annex 1 Monitor (EU GMP Annex 1 해석)
    print("\n[5] Checking GMP Journal Annex 1 content...")
    try:
        annex1_monitor = GMPJournalAnnex1Monitor()
        annex1_result = annex1_monitor.check()

        if annex1_result.get("has_changes"):
            print(f"  -> Changes detected: {annex1_result.get('summary')}")

            # 새 기사 추가
            for article in annex1_result.get("new_articles", []):
                updates.append({
                    "source": "GMP Journal (ECA)",
                    "type": "New Annex 1 Article",
                    "title": article.get("title", "Unknown"),
                    "link": article.get("url", ""),
                    "date": article.get("date", ""),
                    "timestamp": datetime.now().isoformat()
                })

            # 페이지 변경 기록
            for page in annex1_result.get("modified_pages", []):
                updates.append({
                    "source": "GMP Journal (ECA)",
                    "type": "Annex 1 Page Modified",
                    "title": f"Content changed: {page.get('path', '')}",
                    "link": page.get("url", ""),
                    "timestamp": datetime.now().isoformat()
                })

        elif annex1_result.get("status") == "first_check":
            print(f"  -> First check - baseline saved ({annex1_result.get('article_count', 0)} articles, {annex1_result.get('monitored_pages', 0)} pages)")
        else:
            print("  -> No changes detected")

        annex1_count = sum(1 for u in updates if u.get("source") == "GMP Journal (ECA)")
        monitor_results["GMP Journal Annex 1"] = {"status": "ok", "updates": annex1_count}

    except Exception as e:
        print(f"  -> GMP Journal Annex1 check error: {e}")
        monitor_results["GMP Journal Annex 1"] = {"status": "error", "updates": 0, "error": str(e)}
        import traceback
        traceback.print_exc()

    # 6. General Regulatory HTML Pages
    print("\n[6] Checking General Regulatory HTML Pages...")
    try:
        from src.html_change_monitor import RegulatoryPageMonitor
        html_monitor = RegulatoryPageMonitor()
        html_results = html_monitor.check_all()
        
        for res in html_results:
            if res.get("has_changes"):
                # Convert to update format
                updates.append({
                    "source": f"HTML Monitor: {res.get('page_name')}",
                    "type": "Content Change Detected",
                    "title": res.get('description'),
                    "link": res.get('url'),
                    "summary": res.get('summary'),
                    "timestamp": datetime.now().isoformat()
                })
        html_count = sum(1 for r in html_results if r.get("has_changes"))
        monitor_results["HTML Page Monitor"] = {"status": "ok", "updates": html_count}

    except Exception as e:
        print(f"  -> HTML Monitor error: {e}")
        monitor_results["HTML Page Monitor"] = {"status": "error", "updates": 0, "error": str(e)}

    # 7. Save Results
    if updates:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] Saved {len(updates)} updates to {output_file}")
    else:
        print("\n[INFO] No significant updates found in monitors.")
        # Create empty list file to indicate run happened
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

    # 8. Log monitor results to daily log file
    logger.log_monitor_execution(
        monitor_results=monitor_results,
        total_updates=len(updates),
        output_file=output_file
    )

if __name__ == "__main__":
    run_monitor_pipeline()
