import json
import smtplib
import base64
import uuid
import html as html_lib
import re
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
import os

# 프로젝트 루트 및 config 디렉토리 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
import sys
sys.path.insert(0, PROJECT_ROOT)
from src.env_config import first_env, load_project_env

load_project_env()

# 이메일 설정 (.env 파일에서 로드)
SMTP_SERVER = first_env("SMTP_SERVER", default="smtp.gmail.com")
SMTP_PORT = int(first_env("SMTP_PORT", default="587"))
SENDER_EMAIL = first_env("SENDER_EMAIL", "EMAIL_SENDER")
SENDER_PASSWORD = first_env("SENDER_PASSWORD", "EMAIL_PASSWORD")

# 로고 파일 경로
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
    """Return the logo as a base64 string."""
    try:
        with open(LOGO_PATH, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"[WARN] Logo file not found: {LOGO_PATH}")
        return ""


def _load_team_emails_from_file(filepath: str, *, silence_missing: bool = False) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        if not silence_missing:
            print(f"[ERROR] Team email file not found: {filepath}")
        return {}


def _load_team_emails_from_admin_db() -> dict | None:
    if not DATABASE_URL:
        return None

    try:
        import psycopg
    except Exception:
        return None

    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name, COALESCE(description, '')
                    FROM teams
                    WHERE is_active IS TRUE
                    ORDER BY name ASC
                    """
                )
                team_rows = cur.fetchall()

                if not team_rows:
                    return None

                team_map = {
                    str(team_name): {
                        "team_name": str(team_name),
                        "description": str(description or ""),
                        "categories": [],
                        "members": [],
                    }
                    for team_name, description in team_rows
                    if str(team_name or "").strip()
                }

                cur.execute(
                    """
                    SELECT t.name, c.name
                    FROM team_category_map AS tcm
                    JOIN teams AS t
                      ON t.id = tcm.team_id
                    JOIN categories AS c
                      ON c.id = tcm.category_id
                    WHERE t.is_active IS TRUE
                      AND c.is_active IS TRUE
                    ORDER BY t.name ASC, c.name ASC
                    """
                )
                for team_name, category_name in cur.fetchall():
                    team_key = str(team_name or "").strip()
                    category_value = str(category_name or "").strip()
                    if not team_key or not category_value or team_key not in team_map:
                        continue
                    categories = team_map[team_key]["categories"]
                    if category_value not in categories:
                        categories.append(category_value)

                cur.execute(
                    """
                    SELECT t.name, r.email, COALESCE(r.full_name, '')
                    FROM recipient_team_map AS rtm
                    JOIN teams AS t
                      ON t.id = rtm.team_id
                    JOIN recipients AS r
                      ON r.id = rtm.recipient_id
                    WHERE t.is_active IS TRUE
                      AND r.is_active IS TRUE
                    ORDER BY t.name ASC, r.email ASC
                    """
                )
                for team_name, email, full_name in cur.fetchall():
                    team_key = str(team_name or "").strip()
                    email_value = str(email or "").strip().lower()
                    if not team_key or not email_value or team_key not in team_map:
                        continue
                    team_map[team_key]["members"].append(
                        {
                            "email": email_value,
                            "name": str(full_name or "").strip(),
                        }
                    )

                return team_map
    except Exception as e:
        print(f"[WARN] Failed to load team routing from admin DB: {e}")
        return None


def load_team_emails(filepath: str = "team_emails.json") -> dict:
    """Load team/category/member routing for email delivery."""
    db_payload = _load_team_emails_from_admin_db()
    if db_payload:
        return db_payload

    return _load_team_emails_from_file(filepath)


def load_summarized_news(filepath: str) -> list:
    """요약된 뉴스 데이터 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _clip_text(value: str, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _extract_summary_from_jsonish_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith("{"):
        return text

    match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)', text, re.S)
    if match:
        cleaned = match.group(1).replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
        return re.sub(r"\s+", " ", cleaned).strip(" \t\r\n\"',")

    return text


def _resolve_article_summary(article: dict) -> str:
    """Prefer AI summary, but always fall back to scraped summary/content."""
    ai = article.get("ai_analysis", {}) or {}
    summary = (
        ai.get("ai_summary")
        or article.get("summary")
        or article.get("full_text")
        or ""
    )
    summary = _extract_summary_from_jsonish_text(summary)
    summary = _clip_text(summary, limit=360)
    return summary or "No summary available."


def _htmlize_text(value: str) -> str:
    return html_lib.escape(str(value or "")).replace("\n", "<br />")


def _html_to_plain_text(html_content: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def organize_news_by_team(articles: list, team_emails: dict) -> dict:
    """뉴스를 팀별로 분류 (keywords.py 카테고리 기반 매칭)"""
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
    """팀 이메일 HTML 생성 - 인라인 CSS 버전 (이메일 클라이언트 호환)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 모든 스타일을 인라인으로 적용 (이메일 클라이언트 호환용)
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
    
    # AI 키워드가 없는 기사 제외
    articles = [a for a in articles if a.get("ai_analysis", {}).get("ai_keywords")]

    for article in articles:
        ai = article.get("ai_analysis", {})
        title = html_lib.escape(article.get("title", "Untitled"))
        source = html_lib.escape(article.get("source", "Unknown source"))
        published = html_lib.escape(article.get("published", "")[:10] if article.get("published") else "")
        link = html_lib.escape(article.get("link", "#"), quote=True)

        summary = _htmlize_text(_resolve_article_summary(article))
        key_points = [html_lib.escape(str(point)) for point in (ai.get("key_points") or []) if str(point).strip()]
        impact = _htmlize_text(ai.get("industry_impact", ""))
        keywords = [html_lib.escape(str(kw)) for kw in (ai.get("ai_keywords") or []) if str(kw).strip()]
        
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
    """모니터링 업데이트 이메일 HTML 생성 - 인라인 CSS 버전 (이메일 클라이언트 호환)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 모든 스타일을 인라인으로 적용 (이메일 클라이언트 호환용)
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
        
        # AI 결과가 없으면 기본값 사용
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

        alt_part = MIMEMultipart('alternative')
        alt_part.attach(MIMEText(_html_to_plain_text(html_content), 'plain', 'utf-8'))
        html_part = MIMEText(html_content, 'html', 'utf-8')
        alt_part.attach(html_part)
        msg.attach(alt_part)

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
    """Send monitor update emails."""
    print("\n" + "=" * 60)
    print("Monitor Email Delivery Start")
    print("=" * 60)
    
    # 데이터 로드
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        return
        
    with open(updates_json, 'r', encoding='utf-8') as f:
        updates = json.load(f)
    
    if not updates:
        print("[INFO] No monitor updates to send.")
        return

    # 팀별 분류 (AI 분석 결과 기준)
    team_updates = {}
    
    for item in updates:
        ai = item.get("ai_analysis", {})
        target_teams = ai.get("target_teams", [])

        # Fallback: send to all active teams when AI provides no target
        if not target_teams:
            target_teams = list(team_emails.keys())
            if target_teams:
                print(f"[INFO] No AI target teams for monitor update. Sending to all active teams: {target_teams}")
            else:
                print("[WARN] No active teams found. Skipping monitor update item.")
                continue
            
        for team in target_teams:
            # 유사 팀명 매칭 (부분 문자열 사용)
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
                # 매칭 팀이 없는 경우 무시 (전체 발송 폴백 가능)
                pass

    if not team_updates:
        print("[WARN] No matching target teams found for monitor updates. Check RA team naming in team_emails.json.")
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
        
        print(f"\n[{team_name}] Sending {len(update_list)} monitor update(s)...")
        
        if send_email(to_emails, subject, html_content, article_count=len(update_list)):
            print("  -> Sent")
            sent_count += 1
        else:
            print("  -> Failed")
            
    print(f"\n[DONE] Monitor email delivery complete: {sent_count} team(s) sent")


def send_news_to_teams(summarized_json: str, team_emails_json: str = "team_emails.json"):
    """Send news briefing emails by team."""
    print("\n" + "=" * 60)
    print("News Email Delivery Start")
    print("=" * 60)
    
    # 데이터 로드
    team_emails = load_team_emails(team_emails_json)
    if not team_emails:
        print("[SKIP] Team email configuration is missing.")
        return
    
    articles = load_summarized_news(summarized_json)
    team_news = organize_news_by_team(articles, team_emails)
    
    if not team_news:
        print("[SKIP] No news items matched any team.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    sent_count = 0
    skip_count = 0
    
    for team_name, news_list in team_news.items():
        # 해당 팀이 team_emails.json에 있는지 확인
        if team_name not in team_emails:
            print(f"[SKIP] {team_name}: missing team configuration")
            skip_count += 1
            continue
        
        team_info = team_emails[team_name]
        members = team_info.get("members", [])
        
        if not members:
            print(f"[SKIP] {team_name}: no recipients configured")
            skip_count += 1
            continue
        
        # 이메일 주소 추출
        to_emails = [m["email"] for m in members if m.get("email")]
        
        if not to_emails:
            print(f"[SKIP] {team_name}: no recipient email addresses")
            skip_count += 1
            continue
        
        # AI 태그된 기사 필터
        tagged_news = [a for a in news_list if a.get("ai_analysis", {}).get("ai_keywords")]
        if not tagged_news:
            print(f"[SKIP] {team_name}: no tagged news items")
            skip_count += 1
            continue

        # 이메일 제목 및 내용 생성
        subject = f"{team_name} News Briefing - {today} ({len(tagged_news)} items)"
        html_content = create_email_html(team_name, tagged_news)
        
        # 이메일 발송
        print(f"\n[{team_name}] Sending {len(news_list)} news item(s) to {len(to_emails)} recipient(s)...")
        print(f"  To: {', '.join(to_emails)}")
        
        if send_email(to_emails, subject, html_content, article_count=len(tagged_news)):
            print("  -> Sent")
            sent_count += 1
        else:
            print("  -> Failed")
    
    print("\n" + "=" * 60)
    print("News Email Delivery Complete")
    print(f"  Sent: {sent_count} team(s)")
    print(f"  Skipped: {skip_count} team(s)")
    print("=" * 60)


def send_log_email(log_file: str = None):
    """
    매일 실행 로그를 수신자(발신자) 이메일로 발송
    당일 실행 결과를 정해진 수신자에게 전달
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[LOG EMAIL] Sender email configuration is missing.")
        return False

    # 로그 파일 경로 설정
    if log_file is None:
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(PROJECT_ROOT, "logs", f"log_{today}.txt")

    if not os.path.exists(log_file):
        print(f"[LOG EMAIL] Log file not found: {log_file}")
        return False

    # 로그 내용 읽기
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    if not log_content.strip():
        print("[LOG EMAIL] Log file is empty.")
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

    # 최종 HTML 생성
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

    # 수신자에게 이메일로 전송 (발신자 주소로)
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

        print(f"[LOG EMAIL] Log email sent -> {SENDER_EMAIL}")
        return True

    except Exception as e:
        print(f"[LOG EMAIL] Send failed: {e}")
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


# 직접 실행 시
if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Send news or monitor emails")
    parser.add_argument("-i", "--input", help="Input JSON file")
    parser.add_argument("-t", "--teams", default="team_emails.json", help="Team emails JSON file")
    parser.add_argument("--monitor", action="store_true", help="Run in monitor update mode")
    
    args = parser.parse_args()
    
    # 입력 파일 설정
    if args.input:
        input_file = args.input
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"pharma_news_summarized_{today}.json"
    
    print(f"[INFO] Input file: {input_file}")
    print(f"[INFO] Team emails: {args.teams}")
    
    if args.monitor:
        send_monitor_updates(input_file, args.teams)
    else:
        send_news_to_teams(input_file, args.teams)
