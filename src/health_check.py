# System Health Check Script
# 시스템 전체 상태 점검

import sys
sys.path.insert(0, '.')

def check_imports():
    """Import 테스트"""
    results = []
    
    # Core modules
    modules = [
        ("Multi-source Scraper", "multi_source_scraper", "MultiSourceScraper"),
        ("HTML Monitor", "html_change_monitor", "RegulatoryPageMonitor"),
        ("ICH Monitor", "ich_monitor", "ICHGuidelinesMonitor"),
    ]
    
    for name, mod, cls in modules:
        try:
            m = __import__(mod, fromlist=[cls])
            getattr(m, cls)
            results.append((name, "OK"))
        except Exception as e:
            results.append((name, f"FAIL: {e}"))
    
    # Scrapers
    scrapers = [
        ("KPA News", "scrapers.kpanews_scraper", "KPANewsScraper"),
        ("KPBMA", "scrapers.kpbma_scraper", "KPBMAScraper"),
        ("MFDS", "scrapers.mfds_scraper", "MFDSScraper"),
        ("EDQM", "scrapers.edqm_scraper", "EDQMScraper"),
        ("EudraLex", "scrapers.eudralex_scraper", "EudraLexScraper"),
        ("PICS", "scrapers.pics_scraper", "PICSScraper"),
        ("FDA Warning", "scrapers.fda_warning_scraper", "FDAWarningLettersScraper"),
    ]
    
    for name, mod, cls in scrapers:
        try:
            m = __import__(mod, fromlist=[cls])
            getattr(m, cls)
            results.append((name, "OK"))
        except Exception as e:
            results.append((name, f"FAIL: {str(e)[:40]}"))
    
    return results

def check_scraper_fetch(scraper_name, scraper_class, days=1):
    """스크래퍼 실제 실행 테스트"""
    try:
        scraper = scraper_class()
        articles = scraper.fetch_news(days_back=days)
        return (scraper_name, "OK", len(articles))
    except Exception as e:
        return (scraper_name, "FAIL", str(e)[:50])

if __name__ == "__main__":
    print("=" * 60)
    print("SYSTEM HEALTH CHECK")
    print("=" * 60)
    
    # 1. Import check
    print("\n[1] Import Check")
    print("-" * 40)
    import_results = check_imports()
    passed = 0
    for name, status in import_results:
        icon = "[PASS]" if status == "OK" else "[FAIL]"
        print(f"  {icon} {name}")
        if status == "OK":
            passed += 1
    
    print(f"\nImport: {passed}/{len(import_results)} passed")
    
    # 2. Quick fetch test (only if imports pass)
    if passed == len(import_results):
        print("\n[2] Quick Fetch Test (1 day)")
        print("-" * 40)
        
        from scrapers.kpanews_scraper import KPANewsScraper
        from scrapers.mfds_scraper import MFDSScraper
        
        for name, cls in [("KPA News", KPANewsScraper), ("MFDS", MFDSScraper)]:
            try:
                s = cls()
                arts = s.fetch_news(days_back=1)
                print(f"  [PASS] {name}: {len(arts)} articles")
            except Exception as e:
                print(f"  [FAIL] {name}: {str(e)[:40]}")
    
    print("\n" + "=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)
