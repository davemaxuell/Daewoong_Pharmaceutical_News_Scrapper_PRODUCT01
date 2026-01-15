#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test API connectivity (Gemini)
Usage: python tests/test_api.py
"""

import sys
import os
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))


def test_gemini_api():
    """Test Gemini API connectivity"""
    print(f"\n{'='*60}")
    print("Gemini API Connectivity Test")
    print(f"{'='*60}")
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("\n[ERROR] No API key found!")
        print("Set GEMINI_API_KEY in config/.env")
        return False
    
    print(f"\n[INFO] API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        from src.ai_summarizer_gemini import get_gemini_client, MODEL_NAME
        
        print(f"[INFO] Model: {MODEL_NAME}")
        print("[INFO] Initializing client...")
        
        client = get_gemini_client()
        print("[SUCCESS] Client initialized")
        
        # Simple test prompt
        print("\n[INFO] Sending test prompt...")
        start_time = datetime.now()
        
        from google.genai import types
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Say 'Hello, Daewoong!' in Korean. Just the greeting, nothing else.",
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50,
            )
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"[SUCCESS] Response received in {elapsed:.2f}s")
        print(f"\nResponse: {response.text.strip()}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_config():
    """Test email configuration (without sending)"""
    print(f"\n{'='*60}")
    print("Email Configuration Test")
    print(f"{'='*60}")
    
    smtp_server = os.getenv("SMTP_SERVER", "Not set")
    smtp_port = os.getenv("SMTP_PORT", "Not set")
    sender_email = os.getenv("SENDER_EMAIL", "Not set")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    print(f"\nSMTP Server: {smtp_server}")
    print(f"SMTP Port: {smtp_port}")
    print(f"Sender Email: {sender_email}")
    print(f"Password: {'Set' if sender_password else 'NOT SET'}")
    
    if not all([smtp_server != "Not set", sender_email != "Not set", sender_password]):
        print("\n[WARN] Email configuration incomplete")
        return False
    
    print("\n[INFO] Attempting SMTP connection test...")
    
    try:
        import smtplib
        import socket
        
        # Set timeout
        socket.setdefaulttimeout(10)
        
        with smtplib.SMTP(smtp_server, int(smtp_port), timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            print("[SUCCESS] SMTP connection successful (TLS)")
            
            # Try login
            try:
                server.login(sender_email, sender_password)
                print("[SUCCESS] Authentication successful")
            except smtplib.SMTPAuthenticationError as e:
                print(f"[FAILED] Authentication failed: {e}")
                return False
        
        return True
        
    except socket.gaierror as e:
        print(f"[FAILED] DNS resolution failed: {e}")
        print("  -> Check if you're connected to the company network/VPN")
        return False
    except socket.timeout:
        print("[FAILED] Connection timeout")
        return False
    except Exception as e:
        print(f"[FAILED] Connection error: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test API connectivity")
    parser.add_argument("--gemini", "-g", action="store_true", help="Test Gemini API")
    parser.add_argument("--email", "-e", action="store_true", help="Test email config")
    parser.add_argument("--all", "-a", action="store_true", help="Test all APIs")
    
    args = parser.parse_args()
    
    if args.all:
        results = {
            "Gemini API": test_gemini_api(),
            "Email Config": test_email_config()
        }
        
        print("\n" + "="*60)
        print("API Test Summary")
        print("="*60)
        for name, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status}: {name}")
            
    elif args.gemini:
        test_gemini_api()
    elif args.email:
        test_email_config()
    else:
        # Default: test Gemini
        test_gemini_api()
