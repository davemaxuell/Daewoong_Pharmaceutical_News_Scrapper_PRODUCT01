# ?대찓??諛쒖넚 紐⑤뱢
# ?蹂꾨줈 ?댁뒪瑜??뺣━?섏뿬 ?대찓?쇰줈 諛쒖넚?⑸땲??

import json
import smtplib
import base64
import uuid
import html as html_lib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# ?꾨줈?앺듃 猷⑦듃 諛?config ?붾젆?좊━ 寃쎈줈
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
load_dotenv(os.path.join(CONFIG_DIR, ".env"))
import sys
sys.path.insert(0, PROJECT_ROOT)

# ?대찓???ㅼ젙 (.env ?뚯씪?먯꽌 濡쒕뱶)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

# 濡쒓퀬 ?뚯씪 寃쎈줈
LOGO_PATH = os.path.join(PROJECT_ROOT, "assets", "LOGO.png")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
_EMAIL_HISTORY_DISABLED = False
DIAGNOSTICS_LATEST_PATH = os.path.join(PROJECT_ROOT, "data", "diagnostics", "latest_source_health.json")
SOURCE_HEALTH_STALE_DAYS = max(1, int(os.getenv("SOURCE_HEALTH_STALE_DAYS", "7")))
ADMIN_SUMMARY_LOOKBACK_DAYS = max(1, int(os.getenv("ADMIN_SUMMARY_LOOKBACK_DAYS", "7")))


def _db_connect():
    global _EMAIL_HISTORY_DISABLED
    if _EMAIL_HISTORY_DISABLED or not DATABASE_URL:
        return None
    try:
        import psycopg
        return psycopg.connect(DATABASE_URL)
    except Exception as e:
        print(f"[WARN] Email history DB disabled: {e}")
        _EMAIL_HISTORY_DISABLED = True
        return None


def _create_email_campaign(subject: str, html_content: str, article_count: int) -> str | None:
    conn = _db_connect()
    if not conn:
        return None
    campaign_id = str(uuid.uuid4())
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_campaigns (id, subject, body_html, article_count, status)
                    VALUES (%s, %s, %s, %s, 'sending')
                    """,
                    (campaign_id, subject, html_content, max(0, int(article_count or 0))),
                )
        return campaign_id
    except Exception as e:
        print(f"[WARN] Failed to create email campaign history: {e}")
        return None
    finally:
        conn.close()


def _insert_email_deliveries(campaign_id: str, to_emails: list, delivery_type: str = "production"):
    if not campaign_id:
        return
    conn = _db_connect()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                for email in to_emails:
                    email_norm = (email or "").strip().lower()
                    if not email_norm:
                        continue
                    cur.execute("SELECT id FROM recipients WHERE email = %s", (email_norm,))
                    row = cur.fetchone()
                    recipient_id = row[0] if row else None
                    cur.execute(
                        """
                        INSERT INTO email_deliveries (id, campaign_id, recipient_id, email, delivery_type, status)
                        VALUES (%s, %s, %s, %s, %s, 'queued')
                        """,
                        (str(uuid.uuid4()), campaign_id, recipient_id, email_norm, delivery_type),
                    )
    except Exception as e:
        print(f"[WARN] Failed to insert email delivery history: {e}")
    finally:
        conn.close()


def _finalize_email_history(campaign_id: str, success: bool, error_message: str = ""):
    if not campaign_id:
        return
    conn = _db_connect()
    if not conn:
        return
    final_status = "sent" if success else "failed"
    delivery_status = "sent" if success else "failed"
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE email_campaigns
                    SET status = %s, sent_at = NOW()
                    WHERE id = %s
                    """,
                    (final_status, campaign_id),
                )
                if success:
                    cur.execute(
                        """
                        UPDATE email_deliveries
                        SET status = %s, sent_at = NOW()
                        WHERE campaign_id = %s
                        """,
                        (delivery_status, campaign_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE email_deliveries
                        SET status = %s, error_message = %s
                        WHERE campaign_id = %s
                        """,
                        (delivery_status, error_message[:2000], campaign_id),
                    )
    except Exception as e:
        print(f"[WARN] Failed to finalize email history: {e}")
    finally:
        conn.close()


def get_logo_base64() -> str:
    """濡쒓퀬瑜?Base64濡??몄퐫?⑺븯??諛섑솚"""
    try:
        with open(LOGO_PATH, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"[WARN] 濡쒓퀬 ?뚯씪??李얠쓣 ???놁뒿?덈떎: {LOGO_PATH}")
        return ""


def load_team_emails(filepath: str = "team_emails.json") -> dict:
    """?蹂??대찓??二쇱냼 濡쒕뱶"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] {filepath} ?뚯씪??李얠쓣 ???놁뒿?덈떎.")
        return {}


def load_summarized_news(filepath: str) -> list:
    """?붿빟???댁뒪 ?곗씠??濡쒕뱶"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def organize_news_by_team(articles: list, team_emails: dict) -> dict:
    """?댁뒪瑜??蹂꾨줈 遺꾨쪟 (keywords.py 移댄뀒怨좊━ 湲곕컲 ?쇱슦??"""
    team_news = {}

    for team_name, team_info in team_emails.items():
        team_categories = set(team_info.get("categories", []))
        if not team_categories:
            continue

        matching = [
            a for a in articles
            if set(a.get("classifications", [])) & team_categories
            and a.get("ai_analysis", {}).get("ai_keywords")
        ]

        if matching:
            team_news[team_name] = matching

    return team_news


def create_email_html(team_name: str, articles: list) -> str:
    """?蹂??대찓??HTML ?앹꽦 - ?몃씪??CSS 踰꾩쟾 (?ㅼ씠踰?硫붿씪 ?명솚)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 紐⑤뱺 ?ㅽ??쇱쓣 ?몃씪?몄쑝濡??곸슜 (?ㅼ씠踰?硫붿씪 ?명솚??
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
                        <td style="background-color: #f6a04d; padding: 25px 20px; border-radius: 10px 10px 0 0;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="vertical-align: middle; color: #000000;">
                                        <div style="font-size: 20px; font-weight: 600; color: #000000;">{team_name} News Briefing</div>
                                        <div style="font-size: 13px; color: #000000; margin-top: 4px;">{today} | {len(articles)} related articles</div>
                                    </td>
                                    <td style="vertical-align: middle; text-align: right;">
                                        <img src="cid:company_logo" alt="Daewoong Pharmaceutical" style="height: 40px; width: auto;" />
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Orange Divider Line -->
                    <tr>
                        <td style="height: 3px; background-color: #f6a04d; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 20px;">
'''
    
    # ?ㅼ썙?쒓? ?녿뒗 湲곗궗???쒖쇅
    articles = [a for a in articles if a.get("ai_analysis", {}).get("ai_keywords")]

    for article in articles:
        ai = article.get("ai_analysis", {})
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown source")
        published = article.get("published", "")[:10] if article.get("published") else ""
        link = article.get("link", "#")

        summary = ai.get("ai_summary", "No summary available")
        key_points = ai.get("key_points", [])
        impact = ai.get("industry_impact", "")
        keywords = ai.get("ai_keywords", [])
        
        html += f'''
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #FAFAFA; margin-bottom: 15px; border-left: 4px solid #f6a04d; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 17px; color: #333333; font-weight: 600; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 2px solid #f6a04d;">{title}</div>
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
                                                <td style="background-color: #fff0e0; padding: 12px; border-radius: 6px; border-left: 3px solid #f6a04d; font-size: 14px;">
                                                    <strong>Industry Impact:</strong> {impact}
                                                </td>
                                            </tr>
                                        </table>
'''
        
        if keywords:
            html += '<div style="margin-top: 12px;">'
            for kw in keywords:
                html += f'<span style="display: inline-block; background-color: #f6a04d; color: #000000; padding: 4px 10px; border-radius: 12px; font-size: 11px; margin: 2px;">{kw}</span>'
            html += '</div>'
        
        html += f'''
                                        <div style="margin-top: 12px;">
                                            <a href="{link}" target="_blank" style="color: #000000; text-decoration: none; font-weight: 500;">Open original article</a>
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
                            <img src="cid:company_logo" alt="Daewoong Pharmaceutical" style="height: 30px; margin-bottom: 10px;" />
                            <p style="margin: 0;">This email was sent automatically by the Pharma News Agent.</p>
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
    """紐⑤땲?곕쭅 ?낅뜲?댄듃 ?대찓??HTML ?앹꽦 - ?몃씪??CSS 踰꾩쟾 (?ㅼ씠踰?硫붿씪 ?명솚)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 紐⑤뱺 ?ㅽ??쇱쓣 ?몃씪?몄쑝濡??곸슜 (?ㅼ씠踰?硫붿씪 ?명솚??
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
                        <td style="background-color: #f6a04d; padding: 25px 20px; border-radius: 10px 10px 0 0;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="vertical-align: middle; color: #000000;">
                                        <div style="font-size: 20px; font-weight: 600; color: #000000;">{team_name} Regulatory Monitoring Alert</div>
                                        <div style="font-size: 13px; color: #000000; margin-top: 4px;">{today} | {len(updates)} regulatory updates</div>
                                    </td>
                                    <td style="vertical-align: middle; text-align: right;">
                                        <img src="cid:company_logo" alt="Daewoong Pharmaceutical" style="height: 40px; width: auto;" />
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Orange Divider Line -->
                    <tr>
                        <td style="height: 3px; background-color: #f6a04d; font-size: 0; line-height: 0;">&nbsp;</td>
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
        
        # AI 寃곌낵媛 ?놁쑝硫?湲곕낯媛??ъ슜
        summary = ai.get("summary") or ai.get("ai_summary") or item.get("note", "No summary available")
        key_changes = ai.get("key_changes") or ai.get("key_points") or []
        implications = ai.get("implications") or ai.get("industry_impact") or ""
        
        title = f"[{source}] {category.upper()} Update"
        
        html += f'''
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #fff0e0; margin-bottom: 15px; border-left: 4px solid #f6a04d; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <div style="font-size: 17px; color: #d46a00; font-weight: 600; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 2px solid #f6a04d;">{title}</div>
                                        <div style="font-size: 12px; color: #888888; margin-bottom: 10px;">{timestamp} | {source} &gt; {category}</div>
                                        <div style="color: #555555; font-weight: 500; line-height: 1.7;">{summary}</div>
'''
        
        if key_changes:
            html += '''
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 12px;">
                                            <tr>
                                                <td style="background-color: #ffffff; padding: 12px; border: 1px solid #f6c28b; border-radius: 6px;">
                                                    <strong>Key Changes:</strong>
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
                                                <td style="background-color: #fff0e0; padding: 12px; border-radius: 6px; border-left: 3px solid #f6a04d; font-size: 14px;">
                                                    <strong>Impact and Response:</strong> {implications}
                                                </td>
                                            </tr>
                                        </table>
'''
        
        html += f'''
                                        <div style="margin-top: 12px;">
                                            <a href="{link}" target="_blank" style="color: #f6a04d; text-decoration: none; font-weight: 600;">Open source document</a>
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
                            <img src="cid:company_logo" alt="Daewoong Pharmaceutical" style="height: 30px; margin-bottom: 10px;" />
                            <p style="margin: 0;">This alert was generated automatically from the regulatory monitoring system.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''
    
    return html


def send_email(
    to_emails: list,
    subject: str,
    html_content: str,
    article_count: int = 0,
    delivery_type: str = "production",
) -> bool:
    """Email send with DB history persistence."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[ERROR] Sender email config is missing (SENDER_EMAIL/SENDER_PASSWORD).")
        return False

    campaign_id = _create_email_campaign(subject, html_content, article_count)
    _insert_email_deliveries(campaign_id, to_emails, delivery_type=delivery_type)

    try:
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(to_emails)

        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, 'rb') as f:
                logo_img = MIMEImage(f.read(), _subtype='png')
                logo_img.add_header('Content-ID', '<company_logo>')
                logo_img.add_header('Content-Disposition', 'inline', filename='LOGO.png')
                msg.attach(logo_img)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_emails, msg.as_string())

        _finalize_email_history(campaign_id=campaign_id, success=True)
        return True

    except Exception as e:
        print(f"[ERROR] Email send failed: {e}")
        _finalize_email_history(campaign_id=campaign_id, success=False, error_message=str(e))
        return False


def send_monitor_updates(updates_json: str, team_emails_json: str = "team_emails.json"):
    """紐⑤땲?곕쭅 ?낅뜲?댄듃 ?대찓??諛쒖넚"""
    print("\n" + "=" * 60)
    print("?슚 洹쒖젣 紐⑤땲?곕쭅 ?대찓??諛쒖넚 ?쒖옉")
    print("=" * 60)
    
    # ?곗씠??濡쒕뱶
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        return
        
    with open(updates_json, 'r', encoding='utf-8') as f:
        updates = json.load(f)
    
    if not updates:
        print("[INFO] 諛쒖넚???낅뜲?댄듃媛 ?놁뒿?덈떎.")
        return

    # ?蹂?遺꾨쪟 (AI 遺꾩꽍 寃곌낵???곕쫫)
    team_updates = {}
    
    for item in updates:
        ai = item.get("ai_analysis", {})
        target_teams = ai.get("target_teams", [])
        
        # ?寃?????놁쑝硫?RA?(湲곕낯)??諛곗젙
        if not target_teams:
            target_teams = ["RA?", "?덇??", "Regulatory Affairs"] # 湲곕낯媛??쒕룄
            
        for team in target_teams:
            # 留ㅼ묶?섎뒗 ? 李얘린 (遺遺??쇱튂 ?덉슜)
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
                # 留ㅼ묶?섏? ?딆? 寃쎌슦 '?꾩껜怨듭?' ?뱀? 泥ル쾲吏????異붽? (?덉쟾?μ튂)
                pass

    if not team_updates:
        print("[WARN] ?낅뜲?댄듃瑜??섏떊?????李얠? 紐삵뻽?듬땲?? RA? ?ㅼ젙???뺤씤?섏꽭??")
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
        subject = f"[Regulatory Alert] {team_name} - {today} ({len(update_list)} updates)"
        html_content = create_monitor_email_html(team_name, update_list)
        
        print(f"\n[{team_name}] {len(update_list)}嫄댁쓽 洹쒖젣 ?낅뜲?댄듃瑜?諛쒖넚 以?..")
        
        if send_email(to_emails, subject, html_content, article_count=len(update_list)):
            print(f"  ??諛쒖넚 ?꾨즺")
            sent_count += 1
        else:
            print(f"  ??諛쒖넚 ?ㅽ뙣")
            
    print(f"\n[DONE] 珥?{sent_count}媛????紐⑤땲?곕쭅 ?뚮┝ 諛쒖넚 ?꾨즺")


def send_news_to_teams(summarized_json: str, team_emails_json: str = "team_emails.json"):
    """?蹂꾨줈 ?댁뒪 ?대찓??諛쒖넚"""
    print("\n" + "=" * 60)
    print("?벁 ?대찓??諛쒖넚 ?쒖옉")
    print("=" * 60)
    
    # ?곗씠??濡쒕뱶
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        print("[SKIP] ? ?대찓???ㅼ젙???놁뒿?덈떎.")
        return
    
    articles = load_summarized_news(summarized_json)
    team_news = organize_news_by_team(articles, team_emails)
    
    if not team_news:
        print("[SKIP] 諛쒖넚???댁뒪媛 ?놁뒿?덈떎.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    sent_count = 0
    skip_count = 0
    
    for team_name, news_list in team_news.items():
        # ?대떦 ???team_emails.json???덈뒗吏 ?뺤씤
        if team_name not in team_emails:
            print(f"[SKIP] {team_name}: ?대찓???ㅼ젙 ?놁쓬")
            skip_count += 1
            continue
        
        team_info = team_emails[team_name]
        members = team_info.get("members", [])
        
        if not members:
            print(f"[SKIP] {team_name}: ????놁쓬")
            skip_count += 1
            continue
        
        # ?대찓??二쇱냼 異붿텧
        to_emails = [m["email"] for m in members if m.get("email")]
        
        if not to_emails:
            print(f"[SKIP] {team_name}: ?대찓??二쇱냼 ?놁쓬")
            skip_count += 1
            continue
        
        # ?ㅼ썙???녿뒗 湲곗궗 ?쒖쇅
        tagged_news = [a for a in news_list if a.get("ai_analysis", {}).get("ai_keywords")]
        if not tagged_news:
            print(f"[SKIP] {team_name}: ?ㅼ썙???쒓렇???댁뒪 ?놁쓬")
            skip_count += 1
            continue

        # ?대찓???댁슜 ?앹꽦
        subject = f"{team_name} News Briefing - {today} ({len(tagged_news)} items)"
        html_content = create_email_html(team_name, tagged_news)
        
        # ?대찓??諛쒖넚
        print(f"\n[{team_name}] {len(news_list)}嫄댁쓽 ?댁뒪瑜?{len(to_emails)}紐낆뿉寃?諛쒖넚 以?..")
        print(f"  ??? {', '.join(to_emails)}")
        
        if send_email(to_emails, subject, html_content, article_count=len(tagged_news)):
            print(f"  ??諛쒖넚 ?꾨즺!")
            sent_count += 1
        else:
            print(f"  ??諛쒖넚 ?ㅽ뙣")
    
    print("\n" + "=" * 60)
    print(f"?벁 ?대찓??諛쒖넚 ?꾨즺")
    print(f"  ?깃났: {sent_count}媛??")
    print(f"  嫄대꼫?: {skip_count}媛??")
    print("=" * 60)


def send_log_email(log_file: str = None):
    """
    ?쇱씪 ?ㅽ뻾 濡쒓렇瑜?愿由ъ옄(諛쒖떊?? ?대찓?쇰줈 諛쒖넚
    ?뚯씠?꾨씪???ㅽ뻾 寃곌낵瑜?紐⑤땲?곕쭅?섍린 ?꾪븿
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[LOG EMAIL] ?대찓???ㅼ젙???놁뒿?덈떎.")
        return False

    # 濡쒓렇 ?뚯씪 寃쎈줈 寃곗젙
    if log_file is None:
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(PROJECT_ROOT, "logs", f"log_{today}.txt")

    if not os.path.exists(log_file):
        print(f"[LOG EMAIL] 濡쒓렇 ?뚯씪??李얠쓣 ???놁뒿?덈떎: {log_file}")
        return False

    # 濡쒓렇 ?댁슜 ?쎄린
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    if not log_content.strip():
        print("[LOG EMAIL] 濡쒓렇 ?댁슜??鍮꾩뼱?덉뒿?덈떎.")
        return False

    today_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    subject = f"[System Log] Pharma News Agent run result - {today_str}"
    source_health_html = ""

    try:
        if os.path.exists(DIAGNOSTICS_LATEST_PATH):
            with open(DIAGNOSTICS_LATEST_PATH, 'r', encoding='utf-8') as f:
                diagnostics = json.load(f)

            results = diagnostics.get("results", [])
            stale_threshold_days = max(1, int(diagnostics.get("stale_threshold_days", SOURCE_HEALTH_STALE_DAYS)))
            blocked = [item for item in results if item.get("status") == "blocked"]
            unknown = [item for item in results if item.get("status") in {"unknown", "error"}]
            long_stale = []
            now_utc = datetime.now(timezone.utc)

            for item in results:
                if item.get("status") != "stale":
                    continue
                latest = item.get("wide_latest") or item.get("recent_latest")
                if not latest:
                    continue
                try:
                    latest_dt = datetime.fromisoformat(latest)
                    if latest_dt.tzinfo is None:
                        latest_dt = latest_dt.replace(tzinfo=timezone.utc)
                    if (now_utc - latest_dt.astimezone(timezone.utc)).days >= stale_threshold_days:
                        long_stale.append(item)
                except Exception:
                    continue

            if blocked or long_stale or unknown:
                sections = []
                if blocked:
                    blocked_rows = "".join(
                        f"<li><strong>{html_lib.escape(item.get('source_key', '-'))}</strong> - {html_lib.escape(item.get('status_reason', '-'))}</li>"
                        for item in blocked
                    )
                    sections.append(f"<p><strong>Blocked Sources</strong></p><ul>{blocked_rows}</ul>")
                if long_stale:
                    stale_rows = "".join(
                        f"<li><strong>{html_lib.escape(item.get('source_key', '-'))}</strong> - latest {html_lib.escape(str(item.get('wide_latest') or item.get('recent_latest') or '-'))}</li>"
                        for item in long_stale
                    )
                    sections.append(
                        f"<p><strong>Long-Stale Sources ({stale_threshold_days}+ days)</strong></p><ul>{stale_rows}</ul>"
                    )
                if unknown:
                    unknown_rows = "".join(
                        f"<li><strong>{html_lib.escape(item.get('source_key', '-'))}</strong> - {html_lib.escape(item.get('status_reason') or item.get('error') or '-')}</li>"
                        for item in unknown
                    )
                    sections.append(f"<p><strong>Unknown/Error Sources</strong></p><ul>{unknown_rows}</ul>")

                source_health_html = f'''
        <div style="padding: 20px; border-bottom: 1px solid #eee;">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">Source Health Alerts</div>
            <div style="background: #fff7ed; border-left: 4px solid #f6a04d; padding: 14px; border-radius: 6px; font-size: 13px;">
                {"".join(sections)}
            </div>
        </div>'''
    except Exception as e:
        print(f"[LOG EMAIL] Failed to load source health diagnostics: {e}")

    # 媛꾨떒??HTML ?щ㎎
    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 20px; font-family: 'Malgun Gothic', monospace; background-color: #f5f5f5;">
    <div style="max-width: 800px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #333333; color: #ffffff; padding: 20px;">
            <div style="font-size: 18px; font-weight: 600;">System Log - Pharma News Agent</div>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.8;">{today_str}</div>
        </div>
        {source_health_html}
        <div style="padding: 20px;">
            <pre style="background: #f8f8f8; padding: 15px; border-radius: 6px; font-size: 13px; line-height: 1.6; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;">{html_lib.escape(log_content)}</pre>
        </div>
        <div style="text-align: center; padding: 15px; color: #888; font-size: 11px; border-top: 1px solid #eee;">
            Automated delivery - Pharma News Agent system log
        </div>
    </div>
</body>
</html>'''

    # 諛쒖떊???대찓?쇰줈 ?꾩넚 (?먭린 ?먯떊?먭쾶)
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = SENDER_EMAIL

        html_part = MIMEText(html, 'html', 'utf-8')
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [SENDER_EMAIL], msg.as_string())

        print(f"[LOG EMAIL] 濡쒓렇 ?대찓??諛쒖넚 ?꾨즺 -> {SENDER_EMAIL}")
        return True

    except Exception as e:
        print(f"[LOG EMAIL] 諛쒖넚 ?ㅽ뙣: {e}")
        return False


def send_admin_summary_email(days: int = ADMIN_SUMMARY_LOOKBACK_DAYS) -> bool:
    """Send a daily admin operations summary email with CSV attachment."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[ADMIN EMAIL] Sender email config is missing.")
        return False
    if not DATABASE_URL:
        print("[ADMIN EMAIL] DATABASE_URL is missing.")
        return False

    try:
        from src.admin_api.database import SessionLocal
        from src.admin_api.routers.monitor import build_admin_report_csv_text, build_admin_report_payload
    except Exception as e:
        print(f"[ADMIN EMAIL] Failed to load admin report helpers: {e}")
        return False

    db = SessionLocal()
    try:
        payload = build_admin_report_payload(days=days, db=db)
    except Exception as e:
        db.close()
        print(f"[ADMIN EMAIL] Failed to build admin report payload: {e}")
        return False
    finally:
        try:
            db.close()
        except Exception:
            pass

    runs = payload.get("runs", {})
    logs = payload.get("logs", {})
    emails = payload.get("emails", {})
    source_health = payload.get("source_health") or {}
    source_counts = source_health.get("counts", {})
    team_summary = emails.get("team_summary", [])
    recent_campaigns = emails.get("recent_campaigns", [])

    attention_teams = [item for item in team_summary if (item.get("deliveries_failed") or 0) > 0]
    healthy_teams = [item for item in team_summary if (item.get("deliveries_failed") or 0) == 0]

    attention_html = ""
    attention_points = []
    if runs.get("failed", 0):
        attention_points.append(f"<li>Failed runs: <strong>{runs.get('failed', 0)}</strong></li>")
    if logs.get("errors", 0):
        attention_points.append(f"<li>Error logs: <strong>{logs.get('errors', 0)}</strong></li>")
    if source_counts.get("blocked", 0) or source_counts.get("error", 0):
        attention_points.append(
            f"<li>Source health issues: blocked {source_counts.get('blocked', 0)}, error {source_counts.get('error', 0)}</li>"
        )
    if attention_teams:
        attention_points.append(f"<li>Teams with delivery failures: <strong>{len(attention_teams)}</strong></li>")
    if attention_points:
        attention_html = f"""
        <div style="padding: 18px; background: #fff4f2; border-left: 4px solid #c0392b; border-radius: 8px; margin-bottom: 18px;">
            <div style="font-weight: 700; margin-bottom: 8px;">Needs Attention</div>
            <ul style="margin: 0; padding-left: 18px;">{''.join(attention_points)}</ul>
        </div>
        """

    team_rows = "".join(
        f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{html_lib.escape(str(item.get('team_name') or '-'))}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.get('deliveries_sent', 0)}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; color: {'#c0392b' if item.get('deliveries_failed', 0) else '#245d27'};">{item.get('deliveries_failed', 0)}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{html_lib.escape(str(item.get('latest_sent_at') or '-'))}</td>
        </tr>
        """
        for item in team_summary[:20]
    )

    campaign_rows = "".join(
        f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{html_lib.escape(str(item.get('subject') or '-'))}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{html_lib.escape(str(item.get('status') or '-'))}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{item.get('article_count', 0)}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{html_lib.escape(str(item.get('sent_at') or '-'))}</td>
        </tr>
        """
        for item in recent_campaigns[:10]
    )

    generated_at = payload.get("generated_at") or datetime.now().isoformat()
    subject = f"[Admin Summary] Pharma News Agent daily report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    csv_text = build_admin_report_csv_text(payload)
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 20px; font-family: 'Segoe UI', 'Malgun Gothic', Arial, sans-serif; background: #f6f4ef; color: #3a2413;">
  <div style="max-width: 920px; margin: 0 auto; background: #ffffff; border: 1px solid #f0d3b2; border-radius: 14px; overflow: hidden;">
    <div style="background: #ef7d1a; color: #ffffff; padding: 22px;">
      <div style="font-size: 22px; font-weight: 700;">Daily Admin Summary</div>
      <div style="font-size: 13px; opacity: 0.92; margin-top: 6px;">Generated at {html_lib.escape(str(generated_at))} | last {days} days</div>
    </div>
    <div style="padding: 22px;">
      {attention_html}
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px;">
        <div style="padding: 14px; border: 1px solid #f4c79d; border-radius: 10px; background: #fffaf4;">
          <div style="font-weight: 700; margin-bottom: 6px;">Runs</div>
          <div>Total: {runs.get('total', 0)}</div>
          <div>Success: {runs.get('success', 0)}</div>
          <div>Failed: {runs.get('failed', 0)}</div>
        </div>
        <div style="padding: 14px; border: 1px solid #f4c79d; border-radius: 10px; background: #fffaf4;">
          <div style="font-weight: 700; margin-bottom: 6px;">Emails</div>
          <div>Campaigns: {emails.get('campaigns_total', 0)}</div>
          <div>Deliveries: {emails.get('deliveries_total', 0)}</div>
          <div>Failed deliveries: {emails.get('deliveries_failed', 0)}</div>
        </div>
        <div style="padding: 14px; border: 1px solid #f4c79d; border-radius: 10px; background: #fffaf4;">
          <div style="font-weight: 700; margin-bottom: 6px;">Logs</div>
          <div>Errors: {logs.get('errors', 0)}</div>
          <div>Warnings: {logs.get('warnings', 0)}</div>
        </div>
        <div style="padding: 14px; border: 1px solid #f4c79d; border-radius: 10px; background: #fffaf4;">
          <div style="font-weight: 700; margin-bottom: 6px;">Source Health</div>
          <div>Blocked: {source_counts.get('blocked', 0)}</div>
          <div>Stale: {source_counts.get('stale', 0)}</div>
          <div>Error: {source_counts.get('error', 0)}</div>
        </div>
      </div>
      <div style="margin-bottom: 18px;">
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 10px;">Team Delivery Status</div>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; font-size: 13px;">
          <tr style="background: #fff2e2;">
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Team</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Sent</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Failed</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Latest Sent</th>
          </tr>
          {team_rows or '<tr><td colspan="4" style="padding: 8px;">No team delivery history available.</td></tr>'}
        </table>
      </div>
      <div>
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 10px;">Recent Campaigns</div>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; font-size: 13px;">
          <tr style="background: #fff2e2;">
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Subject</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Status</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Articles</th>
            <th align="left" style="padding: 8px; border-bottom: 1px solid #eee;">Sent At</th>
          </tr>
          {campaign_rows or '<tr><td colspan="4" style="padding: 8px;">No recent campaigns.</td></tr>'}
        </table>
      </div>
    </div>
  </div>
</body>
</html>"""

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = SENDER_EMAIL
        msg.attach(MIMEText(html, "html", "utf-8"))

        attachment = MIMEBase("text", "csv")
        attachment.set_payload(csv_text.encode("utf-8"))
        encoders.encode_base64(attachment)
        filename = f"admin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        attachment.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(attachment)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [SENDER_EMAIL], msg.as_string())

        print(f"[ADMIN EMAIL] Daily admin summary sent -> {SENDER_EMAIL}")
        return True
    except Exception as e:
        print(f"[ADMIN EMAIL] Failed to send daily admin summary: {e}")
        return False


# ?⑤룆 ?ㅽ뻾 ??
if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="?蹂??댁뒪 ?대찓??諛쒖넚")
    parser.add_argument("-i", "--input", help="?붿빟???댁뒪 JSON ?뚯씪")
    parser.add_argument("-t", "--teams", default="team_emails.json", help="? ?대찓??JSON ?뚯씪")
    parser.add_argument("--monitor", action="store_true", help="紐⑤땲?곕쭅 ?낅뜲?댄듃 紐⑤뱶濡??ㅽ뻾")
    
    args = parser.parse_args()
    
    # ?낅젰 ?뚯씪 寃곗젙
    if args.input:
        input_file = args.input
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"pharma_news_summarized_{today}.json"
    
    print(f"[INFO] ?낅젰 ?뚯씪: {input_file}")
    print(f"[INFO] ? ?대찓?? {args.teams}")
    
    if args.monitor:
        send_monitor_updates(input_file, args.teams)
    else:
        send_news_to_teams(input_file, args.teams)



