# -*- coding: utf-8 -*-
"""
SMTP Test Script
Tests Naver Works SMTP connection.
"""
import os
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv('config/.env')

# 환경 변수 읽기
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = int(os.getenv('SMTP_PORT', 587))
sender_email = os.getenv('SENDER_EMAIL')
sender_password = os.getenv('SENDER_PASSWORD')

print("=" * 50)
print("SMTP Configuration Test")
print("=" * 50)
print(f"SMTP Server: {smtp_server}")
print(f"SMTP Port: {smtp_port}")
print(f"Sender Email: {sender_email}")
print(f"Password: {'*' * len(sender_password) if sender_password else 'NOT SET'}")
print("=" * 50)

# 비밀번호 확인
if sender_password == 'YOUR_NAVER_WORKS_PASSWORD' or not sender_password:
    print("\n❌ ERROR: Please update SENDER_PASSWORD in config/.env")
    print("   Replace 'YOUR_NAVER_WORKS_PASSWORD' with your actual password")
    sys.exit(1)

# 테스트 이메일 생성
msg = MIMEMultipart()
msg['Subject'] = '[테스트] SMTP 연결 테스트'
msg['From'] = sender_email
msg['To'] = sender_email  # 자신에게 발송

body = """
안녕하세요,

이 이메일은 SMTP 연결 테스트입니다.
이 메일이 도착했다면 SMTP 설정이 성공적으로 완료된 것입니다.

발송 정보:
- SMTP 서버: {smtp_server}
- 포트: {smtp_port}
- 발신자: {sender_email}

감사합니다.
""".format(smtp_server=smtp_server, smtp_port=smtp_port, sender_email=sender_email)

msg.attach(MIMEText(body, 'plain', 'utf-8'))

print("\nConnecting to SMTP server...")
try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.set_debuglevel(1)  # 디버그 출력 활성화
        print("Starting TLS...")
        server.starttls()
        print("Logging in...")
        server.login(sender_email, sender_password)
        print("Sending email...")
        server.send_message(msg)
        print("\n" + "=" * 50)
        print("✅ SUCCESS! Test email sent to:", sender_email)
        print("=" * 50)
except smtplib.SMTPAuthenticationError as e:
    print("\n" + "=" * 50)
    print("❌ AUTHENTICATION FAILED!")
    print("   Check your email and password")
    print(f"   Error: {e}")
    print("=" * 50)
except Exception as e:
    print("\n" + "=" * 50)
    print("❌ ERROR!")
    print(f"   {type(e).__name__}: {e}")
    print("=" * 50)
