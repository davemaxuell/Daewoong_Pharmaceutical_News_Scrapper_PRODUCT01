#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Email Sender 테스트
SMTP 연결, 인증, 이메일 발송 기능을 확인합니다.

Usage:
  python tests/test_email_sender.py                # SMTP 연결 테스트만
  python tests/test_email_sender.py --send EMAIL   # 테스트 이메일 실제 발송
"""

import sys
import os
import argparse
import smtplib
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))


def test_env_config():
    """환경 변수 설정 확인"""
    print("\n[1] Checking email configuration...")

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = os.getenv("SMTP_PORT", "587")
    sender_email = os.getenv("SENDER_EMAIL", "")
    sender_password = os.getenv("SENDER_PASSWORD", "")

    print(f"  -> SMTP Server: {smtp_server}:{smtp_port}")
    print(f"  -> Sender Email: {sender_email or '(not set)'}")
    print(f"  -> Password: {'****' + sender_password[-4:] if len(sender_password) > 4 else '(not set)'}")

    if not sender_email:
        print("  -> [FAIL] SENDER_EMAIL not set in .env")
        return False
    if not sender_password:
        print("  -> [FAIL] SENDER_PASSWORD not set in .env")
        return False

    print("  -> [PASS] Email config OK")
    return True


def test_smtp_connection():
    """SMTP 서버 연결 테스트"""
    print("\n[2] Testing SMTP connection...")

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            print(f"  -> Connected to {smtp_server}:{smtp_port}")
            print("  -> TLS handshake OK")
            print("  -> [PASS] SMTP connection successful")
            return True
    except smtplib.SMTPConnectError as e:
        print(f"  -> [FAIL] Connection refused: {e}")
        return False
    except Exception as e:
        print(f"  -> [FAIL] Connection error: {e}")
        return False


def test_smtp_auth():
    """SMTP 인증 테스트"""
    print("\n[3] Testing SMTP authentication...")

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL", "")
    sender_password = os.getenv("SENDER_PASSWORD", "")

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            print(f"  -> Logged in as {sender_email}")
            print("  -> [PASS] Authentication successful")
            return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"  -> [FAIL] Authentication failed: {e}")
        print("  -> Check SENDER_PASSWORD (use app password for Gmail)")
        return False
    except Exception as e:
        print(f"  -> [FAIL] Auth error: {e}")
        return False


def test_team_emails():
    """팀 이메일 설정 파일 확인"""
    print("\n[4] Checking team emails config...")

    team_emails_path = os.path.join(PROJECT_ROOT, "config", "team_emails.json")

    if not os.path.exists(team_emails_path):
        print(f"  -> [WARN] {team_emails_path} not found")
        return False

    try:
        import json
        with open(team_emails_path, 'r', encoding='utf-8') as f:
            teams = json.load(f)

        print(f"  -> Found {len(teams)} teams:")
        for team_name, team_data in teams.items():
            emails = team_data.get("emails", [])
            print(f"     - {team_name}: {len(emails)} recipients")

        print("  -> [PASS] Team emails config OK")
        return True

    except Exception as e:
        print(f"  -> [FAIL] Error reading team emails: {e}")
        return False


def test_logo():
    """로고 파일 존재 확인"""
    print("\n[5] Checking logo file...")

    logo_path = os.path.join(PROJECT_ROOT, "assets", "LOGO.png")

    if os.path.exists(logo_path):
        size = os.path.getsize(logo_path)
        print(f"  -> Logo found: {logo_path} ({size} bytes)")
        print("  -> [PASS] Logo file OK")
        return True
    else:
        print(f"  -> [WARN] Logo not found: {logo_path}")
        print("  -> Emails will be sent without logo")
        return True  # Not critical


def send_test_email(to_email: str):
    """테스트 이메일 발송"""
    print(f"\n[6] Sending test email to {to_email}...")

    from src.email_sender import send_email

    test_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Pharmaceutical News Agent - Test Email</h2>
        <p>This is a test email to verify the email sending system.</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            If you received this email, the email system is working correctly.
        </p>
    </body>
    </html>
    """

    subject = f"[TEST] Pharma News Agent - Email Test ({datetime.now().strftime('%H:%M')})"

    try:
        success = send_email([to_email], subject, test_html)
        if success:
            print(f"  -> [PASS] Test email sent to {to_email}")
        else:
            print("  -> [FAIL] send_email returned False")
        return success
    except Exception as e:
        print(f"  -> [FAIL] Send error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Email Sender Test")
    parser.add_argument("--send", metavar="EMAIL", help="Send a test email to this address")
    args = parser.parse_args()

    print("=" * 60)
    print("Email Sender Test")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Step 1: Config check
    config_ok = test_env_config()
    if not config_ok:
        print("\n[RESULT] FAIL - Fix .env configuration first")
        return

    # Step 2: SMTP connection
    conn_ok = test_smtp_connection()

    # Step 3: Authentication
    auth_ok = False
    if conn_ok:
        auth_ok = test_smtp_auth()

    # Step 4: Team emails
    test_team_emails()

    # Step 5: Logo
    test_logo()

    # Step 6: Send test email (optional)
    if args.send and auth_ok:
        send_test_email(args.send)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Config:     {'PASS' if config_ok else 'FAIL'}")
    print(f"  Connection: {'PASS' if conn_ok else 'FAIL'}")
    print(f"  Auth:       {'PASS' if auth_ok else 'FAIL'}")

    if auth_ok and not args.send:
        print("\n  To send a test email, run:")
        print("  python tests/test_email_sender.py --send your@email.com")

    print("=" * 60)


if __name__ == "__main__":
    main()
