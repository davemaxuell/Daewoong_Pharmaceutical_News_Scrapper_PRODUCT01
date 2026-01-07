# 이메일 발송 모듈
# 팀별로 뉴스를 정리하여 이메일로 발송합니다.

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# 이메일 설정 (.env 파일에서 로드)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")


def load_team_emails(filepath: str = "team_emails.json") -> dict:
    """팀별 이메일 주소 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] {filepath} 파일을 찾을 수 없습니다.")
        return {}


def load_summarized_news(filepath: str) -> list:
    """요약된 뉴스 데이터 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def organize_news_by_team(articles: list) -> dict:
    """뉴스를 팀별로 분류"""
    team_news = {}
    
    for article in articles:
        ai_analysis = article.get("ai_analysis", {})
        target_teams = ai_analysis.get("target_teams", [])
        
        # 타겟 팀이 없으면 건너뜀
        if not target_teams:
            continue
        
        for team in target_teams:
            if team not in team_news:
                team_news[team] = []
            team_news[team].append(article)
    
    return team_news


def create_email_html(team_name: str, articles: list) -> str:
    """팀별 이메일 HTML 생성"""
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .article {{ background: #f8f9fa; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; }}
            .article h2 {{ margin: 0 0 10px 0; font-size: 18px; color: #2c3e50; }}
            .article .meta {{ font-size: 12px; color: #666; margin-bottom: 10px; }}
            .article .summary {{ color: #444; }}
            .article .key-points {{ margin: 10px 0; padding-left: 20px; }}
            .article .key-points li {{ margin: 5px 0; }}
            .article .impact {{ background: #e8f4fd; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 14px; }}
            .article .keywords {{ margin-top: 10px; }}
            .article .keyword {{ display: inline-block; background: #667eea; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; margin: 2px; }}
            .article .link {{ margin-top: 10px; }}
            .article .link a {{ color: #667eea; text-decoration: none; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📰 {team_name} 뉴스 브리핑</h1>
                <p>{today} | {len(articles)}건의 관련 뉴스</p>
            </div>
    """
    
    for article in articles:
        ai = article.get("ai_analysis", {})
        title = article.get("title", "제목 없음")
        source = article.get("source", "출처 미상")
        published = article.get("published", "")[:10] if article.get("published") else ""
        link = article.get("link", "#")
        
        summary = ai.get("ai_summary", "요약 없음")
        key_points = ai.get("key_points", [])
        impact = ai.get("industry_impact", "")
        keywords = ai.get("ai_keywords", [])
        
        html += f"""
            <div class="article">
                <h2>{title}</h2>
                <div class="meta">{source} | {published}</div>
                <div class="summary">{summary}</div>
        """
        
        if key_points:
            html += '<ul class="key-points">'
            for point in key_points:
                html += f'<li>{point}</li>'
            html += '</ul>'
        
        if impact:
            html += f'<div class="impact">💡 <strong>업계 영향:</strong> {impact}</div>'
        
        if keywords:
            html += '<div class="keywords">'
            for kw in keywords:
                html += f'<span class="keyword">{kw}</span>'
            html += '</div>'
        
        html += f'''
                <div class="link"><a href="{link}" target="_blank">🔗 원문 보기</a></div>
            </div>
        '''
    
    html += """
            <div class="footer">
                <p>이 이메일은 제약 뉴스 에이전트에 의해 자동으로 발송되었습니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def create_monitor_email_html(team_name: str, updates: list) -> str:
    """모니터링 업데이트 이메일 HTML 생성"""
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #FF512F 0%, #DD2476 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .update {{ background: #fff5f5; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #DD2476; }}
            .update h2 {{ margin: 0 0 10px 0; font-size: 18px; color: #c0392b; }}
            .update .meta {{ font-size: 12px; color: #666; margin-bottom: 10px; }}
            .update .summary {{ color: #444; font-weight: bold; }}
            .update .changes {{ margin: 10px 0; background: white; padding: 10px; border: 1px solid #eee; }}
            .update .changes li {{ margin: 5px 0; }}
            .update .implications {{ background: #ffeaa7; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 14px; }}
            .update .link {{ margin-top: 10px; }}
            .update .link a {{ color: #DD2476; text-decoration: none; font-weight: bold; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚨 {team_name} 규제 모니터링 알림</h1>
                <p>{today} | {len(updates)}건의 규제 업데이트</p>
            </div>
    """
    
    for item in updates:
        ai = item.get("ai_analysis", {})
        source = item.get("source", "Unknown Source")
        category = item.get("category", "")
        link = item.get("link", "#")
        timestamp = item.get("timestamp", "")[:10]
        
        # AI 결과가 없으면 기본값 사용
        summary = ai.get("summary") or ai.get("ai_summary") or item.get("note", "내용 없음")
        key_changes = ai.get("key_changes") or ai.get("key_points") or []
        implications = ai.get("implications") or ai.get("industry_impact") or ""
        
        title = f"[{source}] {category.upper()} 업데이트"
        
        html += f"""
            <div class="update">
                <h2>{title}</h2>
                <div class="meta">{timestamp} | {source} > {category}</div>
                <div class="summary">{summary}</div>
        """
        
        if key_changes:
            html += '<div class="changes"><strong>📋 주요 변경사항:</strong><ul>'
            for change in key_changes:
                html += f'<li>{change}</li>'
            html += '</ul></div>'
        
        if implications:
            html += f'<div class="implications">⚠️ <strong>영향 및 대응:</strong> {implications}</div>'
            
        html += f'''
                <div class="link"><a href="{link}" target="_blank">📄 원문 문서 보기</a></div>
            </div>
        '''
    
    html += """
            <div class="footer">
                <p>이 알림은 규제 모니터링 시스템에 의해 감지된 중요 변경사항입니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(to_emails: list, subject: str, html_content: str) -> bool:
    """이메일 발송"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[ERROR] 이메일 설정이 없습니다. .env 파일에 SENDER_EMAIL, SENDER_PASSWORD를 설정하세요.")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(to_emails)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_emails, msg.as_string())
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 이메일 발송 실패: {e}")
        return False


def send_monitor_updates(updates_json: str, team_emails_json: str = "team_emails.json"):
    """모니터링 업데이트 이메일 발송"""
    print("\n" + "=" * 60)
    print("🚨 규제 모니터링 이메일 발송 시작")
    print("=" * 60)
    
    # 데이터 로드
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        return
        
    with open(updates_json, 'r', encoding='utf-8') as f:
        updates = json.load(f)
    
    if not updates:
        print("[INFO] 발송할 업데이트가 없습니다.")
        return

    # 팀별 분류 (AI 분석 결과에 따름)
    team_updates = {}
    
    for item in updates:
        ai = item.get("ai_analysis", {})
        target_teams = ai.get("target_teams", [])
        
        # 타겟 팀이 없으면 RA팀(기본)에 배정
        if not target_teams:
            target_teams = ["RA팀", "허가팀", "Regulatory Affairs"] # 기본값 시도
            
        for team in target_teams:
            # 매칭되는 팀 찾기 (부분 일치 허용)
            matched_team = None
            for defined_team in team_emails.keys():
                if team in defined_team or defined_team in team:
                    matched_team = defined_team
                    break
            
            if matched_team:
                if matched_team not in team_updates:
                    team_updates[matched_team] = []
                team_updates[matched_team].append(item)
            else:
                # 매칭되지 않은 경우 '전체공지' 혹은 첫번째 팀에 추가 (안전장치)
                pass

    if not team_updates:
        print("[WARN] 업데이트를 수신할 팀을 찾지 못했습니다. RA팀 설정을 확인하세요.")
        return

    sent_count = 0
    
    for team_name, update_list in team_updates.items():
        if team_name not in team_emails:
            continue
            
        team_info = team_emails[team_name]
        members = team_info.get("members", [])
        to_emails = [m["email"] for m in members if m.get("email")]
        
        if not to_emails:
            continue
            
        today = datetime.now().strftime('%Y-%m-%d')
        subject = f"[규제 긴급 알림] {team_name} - {today} ({len(update_list)}건)"
        html_content = create_monitor_email_html(team_name, update_list)
        
        print(f"\n[{team_name}] {len(update_list)}건의 규제 업데이트를 발송 중...")
        
        if send_email(to_emails, subject, html_content):
            print(f"  ✅ 발송 완료")
            sent_count += 1
        else:
            print(f"  ❌ 발송 실패")
            
    print(f"\n[DONE] 총 {sent_count}개 팀에 모니터링 알림 발송 완료")


def send_news_to_teams(summarized_json: str, team_emails_json: str = "team_emails.json"):
    """팀별로 뉴스 이메일 발송"""
    print("\n" + "=" * 60)
    print("📧 이메일 발송 시작")
    print("=" * 60)
    
    # 데이터 로드
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        print("[SKIP] 팀 이메일 설정이 없습니다.")
        return
    
    articles = load_summarized_news(summarized_json)
    team_news = organize_news_by_team(articles)
    
    if not team_news:
        print("[SKIP] 발송할 뉴스가 없습니다.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    sent_count = 0
    skip_count = 0
    
    for team_name, news_list in team_news.items():
        # 해당 팀이 team_emails.json에 있는지 확인
        if team_name not in team_emails:
            print(f"[SKIP] {team_name}: 이메일 설정 없음")
            skip_count += 1
            continue
        
        team_info = team_emails[team_name]
        members = team_info.get("members", [])
        
        if not members:
            print(f"[SKIP] {team_name}: 팀원 없음")
            skip_count += 1
            continue
        
        # 이메일 주소 추출
        to_emails = [m["email"] for m in members if m.get("email")]
        
        if not to_emails:
            print(f"[SKIP] {team_name}: 이메일 주소 없음")
            skip_count += 1
            continue
        
        # 이메일 내용 생성
        subject = f"[제약 뉴스 브리핑] {team_name} - {today} ({len(news_list)}건)"
        html_content = create_email_html(team_name, news_list)
        
        # 이메일 발송
        print(f"\n[{team_name}] {len(news_list)}건의 뉴스를 {len(to_emails)}명에게 발송 중...")
        print(f"  대상: {', '.join(to_emails)}")
        
        if send_email(to_emails, subject, html_content):
            print(f"  ✅ 발송 완료!")
            sent_count += 1
        else:
            print(f"  ❌ 발송 실패")
    
    print("\n" + "=" * 60)
    print(f"📧 이메일 발송 완료")
    print(f"  성공: {sent_count}개 팀")
    print(f"  건너뜀: {skip_count}개 팀")
    print("=" * 60)


# 단독 실행 시
if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="팀별 뉴스 이메일 발송")
    parser.add_argument("-i", "--input", help="요약된 뉴스 JSON 파일")
    parser.add_argument("-t", "--teams", default="team_emails.json", help="팀 이메일 JSON 파일")
    parser.add_argument("--monitor", action="store_true", help="모니터링 업데이트 모드로 실행")
    
    args = parser.parse_args()
    
    # 입력 파일 결정
    if args.input:
        input_file = args.input
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"pharma_news_summarized_{today}.json"
    
    print(f"[INFO] 입력 파일: {input_file}")
    print(f"[INFO] 팀 이메일: {args.teams}")
    
    if args.monitor:
        send_monitor_updates(input_file, args.teams)
    else:
        send_news_to_teams(input_file, args.teams)
