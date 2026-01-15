#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test team routing and configuration
Usage: python tests/test_teams.py
       python tests/test_teams.py --category "품질시스템/QMS"
"""

import sys
import os
import argparse
import json

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.team_definitions import (
    TEAM_DEFINITIONS, 
    get_team_list, 
    get_team_prompt, 
    get_team_categories,
    get_teams_by_category
)


def test_team_definitions():
    """Test team definitions are properly configured"""
    print(f"\n{'='*60}")
    print("Team Definitions Test")
    print(f"{'='*60}")
    
    teams = get_team_list()
    print(f"\nTotal teams: {len(teams)}")
    print("-" * 40)
    
    for team in teams:
        info = TEAM_DEFINITIONS[team]
        categories = info.get("categories", [])
        keywords = info.get("keywords", [])
        
        print(f"\n📋 {team}")
        print(f"   Description: {info['description'][:60]}...")
        print(f"   Categories: {len(categories)} assigned")
        for cat in categories:
            print(f"     - {cat}")
        print(f"   Keywords: {len(keywords)} defined")
    
    return True


def test_team_emails():
    """Test team_emails.json configuration"""
    print(f"\n{'='*60}")
    print("Team Emails Configuration Test")
    print(f"{'='*60}")
    
    emails_path = os.path.join(PROJECT_ROOT, "config", "team_emails.json")
    
    if not os.path.exists(emails_path):
        print(f"[ERROR] team_emails.json not found at: {emails_path}")
        return False
    
    with open(emails_path, 'r', encoding='utf-8') as f:
        team_emails = json.load(f)
    
    print(f"\nTeams in config: {len(team_emails)}")
    print("-" * 40)
    
    teams_in_definitions = set(get_team_list())
    teams_in_emails = set(team_emails.keys())
    
    # Check for mismatches
    missing_in_emails = teams_in_definitions - teams_in_emails
    extra_in_emails = teams_in_emails - teams_in_definitions
    
    for team_name, team_info in team_emails.items():
        members = team_info.get("members", [])
        categories = team_info.get("categories", [])
        
        status = "✓" if team_name in teams_in_definitions else "⚠"
        print(f"\n{status} {team_name}")
        print(f"   Members: {len(members)}")
        for m in members:
            print(f"     - {m.get('name', 'N/A')}: {m.get('email', 'N/A')}")
        print(f"   Categories: {categories}")
    
    if missing_in_emails:
        print(f"\n⚠ Teams in definitions but NOT in emails: {missing_in_emails}")
    if extra_in_emails:
        print(f"\n⚠ Teams in emails but NOT in definitions: {extra_in_emails}")
    
    return True


def test_category_routing(category: str = None):
    """Test which teams receive which categories"""
    print(f"\n{'='*60}")
    print("Category-to-Team Routing Test")
    print(f"{'='*60}")
    
    if category:
        teams = get_teams_by_category(category)
        print(f"\nCategory: {category}")
        print(f"Teams: {teams if teams else 'None assigned'}")
    else:
        # Show all category mappings
        from src.keywords import get_categories
        
        all_categories = get_categories()
        print(f"\nTotal categories: {len(all_categories)}")
        print("-" * 40)
        
        for cat in all_categories:
            teams = get_teams_by_category(cat)
            teams_str = ", ".join(teams) if teams else "❌ No team assigned"
            print(f"  {cat}")
            print(f"    → {teams_str}")
    
    return True


def test_llm_prompt():
    """Test LLM prompt generation"""
    print(f"\n{'='*60}")
    print("LLM Team Prompt Test")
    print(f"{'='*60}")
    
    prompt = get_team_prompt()
    print("\nGenerated prompt for LLM:")
    print("-" * 40)
    print(prompt)
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test team routing")
    parser.add_argument("--category", "-c", help="Test routing for specific category")
    parser.add_argument("--emails", "-e", action="store_true", help="Test email config")
    parser.add_argument("--prompt", "-p", action="store_true", help="Show LLM prompt")
    parser.add_argument("--all", "-a", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.all:
        test_team_definitions()
        test_team_emails()
        test_category_routing()
        test_llm_prompt()
    elif args.category:
        test_category_routing(args.category)
    elif args.emails:
        test_team_emails()
    elif args.prompt:
        test_llm_prompt()
    else:
        test_team_definitions()
        test_category_routing()
