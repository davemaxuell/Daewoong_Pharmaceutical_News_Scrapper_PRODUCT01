# 이메일 발송 모듈
# 팀별로 뉴스를 정리하여 이메일로 발송합니다.

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

# 프로젝트 루트 및 config 디렉토리 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
load_dotenv(os.path.join(CONFIG_DIR, ".env"))

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
    """팀별 이메일 HTML 생성 - 인라인 CSS 버전 (네이버 메일 호환)"""
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    # 모든 스타일을 인라인으로 적용 (네이버 메일 호환성)
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif; line-height: 1.6; color: #4D4D4D; background-color: #f5f5f5;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px;">
                <table cellpadding="0" cellspacing="0" border="0" width="900" style="max-width: 900px; background-color: #ffffff;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #F7941D; padding: 25px 20px; border-radius: 10px 10px 0 0;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="vertical-align: middle; color: #ffffff;">
                                        <div style="font-size: 20px; font-weight: 600; color: #ffffff;">📰 {team_name} 뉴스 브리핑</div>
                                        <div style="font-size: 13px; color: #ffffff; opacity: 0.95; margin-top: 4px;">{today} | {len(articles)}건의 관련 뉴스</div>
                                    </td>
                                    <td style="vertical-align: middle; text-align: right; color: #ffffff;">
                                        <div style="font-size: 18px; font-weight: 700; letter-spacing: 2px; color: #ffffff;">DAEWOONG</div>
                                        <div style="font-size: 10px; color: #ffffff; opacity: 0.8; margin-top: 2px;">PHARMACEUTICAL</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 20px;">
'''
    
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
        
        html += f'''
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #FAFAFA; margin-bottom: 15px; border-left: 4px solid #F7941D; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 17px; color: #333333; font-weight: 600; margin-bottom: 10px;">{title}</div>
                                        <div style="font-size: 12px; color: #888888; margin-bottom: 10px;">{source} | {published}</div>
                                        <div style="color: #555555; line-height: 1.7;">{summary}</div>
'''
        
        if key_points:
            html += '<ul style="margin: 12px 0; padding-left: 20px; color: #555555;">'
            for point in key_points:
                html += f'<li style="margin: 6px 0;">{point}</li>'
            html += '</ul>'
        
        if impact:
            html += f'''
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 12px;">
                                            <tr>
                                                <td style="background-color: #FEF4E8; padding: 12px; border-radius: 6px; border-left: 3px solid #F7941D; font-size: 14px;">
                                                    💡 <strong>업계 영향:</strong> {impact}
                                                </td>
                                            </tr>
                                        </table>
'''
        
        if keywords:
            html += '<div style="margin-top: 12px;">'
            for kw in keywords:
                html += f'<span style="display: inline-block; background-color: #F7941D; color: #ffffff; padding: 4px 10px; border-radius: 12px; font-size: 11px; margin: 2px;">{kw}</span>'
            html += '</div>'
        
        html += f'''
                                        <div style="margin-top: 12px;">
                                            <a href="{link}" target="_blank" style="color: #F7941D; text-decoration: none; font-weight: 500;">🔗 원문 보기</a>
                                        </div>
                                    </td>
                                </tr>
                            </table>
'''
    
    html += '''
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="text-align: center; padding: 25px 20px; color: #888888; font-size: 12px; border-top: 1px solid #eeeeee;">
                            <p style="color: #F7941D; font-weight: 500; margin: 0 0 10px 0;">DAEWOONG PHARMACEUTICAL</p>
                            <p style="margin: 0;">이 이메일은 제약 뉴스 에이전트에 의해 자동으로 발송되었습니다.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''
    
    return html




def create_monitor_email_html(team_name: str, updates: list) -> str:
    """모니터링 업데이트 이메일 HTML 생성 - 인라인 CSS 버전 (네이버 메일 호환)"""
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    # 모든 스타일을 인라인으로 적용 (네이버 메일 호환성)
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif; line-height: 1.6; color: #4D4D4D; background-color: #f5f5f5;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 20px;">
                <table cellpadding="0" cellspacing="0" border="0" width="900" style="max-width: 900px; background-color: #ffffff;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #E67E22; padding: 25px 20px; border-radius: 10px 10px 0 0;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="vertical-align: middle; color: #ffffff;">
                                        <div style="font-size: 20px; font-weight: 600; color: #ffffff;">🚨 {team_name} 규제 모니터링 알림</div>
                                        <div style="font-size: 13px; color: #ffffff; opacity: 0.95; margin-top: 4px;">{today} | {len(updates)}건의 규제 업데이트</div>
                                    </td>
                                    <td style="vertical-align: middle; text-align: right; color: #ffffff;">
                                        <div style="font-size: 18px; font-weight: 700; letter-spacing: 2px; color: #ffffff;">DAEWOONG</div>
                                        <div style="font-size: 10px; color: #ffffff; opacity: 0.8; margin-top: 2px;">PHARMACEUTICAL</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 20px;">
'''
    
    for item in updates:
        ai = item.get("ai_analysis", {})
        source = item.get("source", "Unknown Source")
        category = item.get("category", "")
        link = item.get("link", "#")
        timestamp = item.get("timestamp", "")[:10] if item.get("timestamp") else ""
        
        # AI 결과가 없으면 기본값 사용
        summary = ai.get("summary") or ai.get("ai_summary") or item.get("note", "내용 없음")
        key_changes = ai.get("key_changes") or ai.get("key_points") or []
        implications = ai.get("implications") or ai.get("industry_impact") or ""
        
        title = f"[{source}] {category.upper()} 업데이트"
        
        html += f'''
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #FEF9F3; margin-bottom: 15px; border-left: 4px solid #E67E22; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 17px; color: #D35400; font-weight: 600; margin-bottom: 10px;">{title}</div>
                                        <div style="font-size: 12px; color: #888888; margin-bottom: 10px;">{timestamp} | {source} &gt; {category}</div>
                                        <div style="color: #555555; font-weight: 500; line-height: 1.7;">{summary}</div>
'''
        
        if key_changes:
            html += '''
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 12px;">
                                            <tr>
                                                <td style="background-color: #ffffff; padding: 12px; border: 1px solid #F5DCC3; border-radius: 6px;">
                                                    <strong>📋 주요 변경사항:</strong>
                                                    <ul style="margin: 8px 0 0 0; padding-left: 20px;">'''
            for change in key_changes:
                html += f'<li style="margin: 6px 0; color: #555555;">{change}</li>'
            html += '''</ul>
                                                </td>
                                            </tr>
                                        </table>
'''
        
        if implications:
            html += f'''
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 12px;">
                                            <tr>
                                                <td style="background-color: #FEF4E8; padding: 12px; border-radius: 6px; border-left: 3px solid #E67E22; font-size: 14px;">
                                                    ⚠️ <strong>영향 및 대응:</strong> {implications}
                                                </td>
                                            </tr>
                                        </table>
'''
        
        html += f'''
                                        <div style="margin-top: 12px;">
                                            <a href="{link}" target="_blank" style="color: #D35400; text-decoration: none; font-weight: 600;">📄 원문 문서 보기</a>
                                        </div>
                                    </td>
                                </tr>
                            </table>
'''
    
    html += '''
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="text-align: center; padding: 25px 20px; color: #888888; font-size: 12px; border-top: 1px solid #eeeeee;">
                            <p style="color: #E67E22; font-weight: 500; margin: 0 0 10px 0;">DAEWOONG PHARMACEUTICAL</p>
                            <p style="margin: 0;">이 알림은 규제 모니터링 시스템에 의해 감지된 중요 변경사항입니다.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''
    
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
