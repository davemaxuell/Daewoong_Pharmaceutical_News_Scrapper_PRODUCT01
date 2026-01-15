#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test keyword classification
Usage: python tests/test_keywords.py --text "FDA CAPA deviation 일탈"
       python tests/test_keywords.py --interactive
       python tests/test_keywords.py --categories
"""

import sys
import os
import argparse

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.keywords import classify_article, get_categories, get_gmp_categories, KEYWORDS


def test_classification(text: str):
    """Test keyword classification on given text"""
    print(f"\n{'='*60}")
    print("Keyword Classification Test")
    print(f"{'='*60}")
    print(f"\nInput text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print("-" * 40)
    
    categories, keywords = classify_article(text)
    
    if categories:
        print(f"\n✓ Classifications: {len(categories)} found")
        for cat in categories:
            print(f"  - {cat}")
    else:
        print("\n✗ No classifications matched")
    
    if keywords:
        print(f"\n✓ Matched Keywords: {len(keywords)} found")
        for kw in keywords[:10]:
            print(f"  - {kw}")
        if len(keywords) > 10:
            print(f"  ... and {len(keywords) - 10} more")
    else:
        print("\n✗ No keywords matched")
    
    return categories, keywords


def show_categories():
    """Show all available categories"""
    print(f"\n{'='*60}")
    print("Available Categories")
    print(f"{'='*60}")
    
    all_cats = get_categories()
    gmp_cats = get_gmp_categories()
    
    print(f"\nTotal: {len(all_cats)} categories")
    print(f"GMP/QMS categories: {len(gmp_cats)}")
    
    print("\n--- News Categories ---")
    for cat in all_cats:
        if cat not in gmp_cats:
            kw_count = len(KEYWORDS.get(cat, []))
            print(f"  {cat} ({kw_count} keywords)")
    
    print("\n--- GMP/QMS Categories ---")
    for cat in gmp_cats:
        kw_count = len(KEYWORDS.get(cat, []))
        print(f"  {cat} ({kw_count} keywords)")


def show_category_keywords(category: str):
    """Show keywords for a specific category"""
    if category not in KEYWORDS:
        print(f"[ERROR] Unknown category: {category}")
        return
    
    keywords = KEYWORDS[category]
    print(f"\n{'='*60}")
    print(f"Keywords in '{category}'")
    print(f"{'='*60}")
    print(f"Total: {len(keywords)} keywords")
    print("-" * 40)
    
    for i, kw in enumerate(keywords, 1):
        print(f"  {i:3}. {kw}")


def interactive_mode():
    """Interactive classification testing"""
    print(f"\n{'='*60}")
    print("Interactive Keyword Test Mode")
    print("Type 'quit' to exit, 'categories' to list all")
    print(f"{'='*60}")
    
    while True:
        text = input("\n> Enter text to classify: ").strip()
        
        if text.lower() == 'quit':
            break
        elif text.lower() == 'categories':
            show_categories()
        elif text.startswith('show:'):
            category = text[5:].strip()
            show_category_keywords(category)
        elif text:
            test_classification(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test keyword classification")
    parser.add_argument("--text", "-t", help="Text to classify")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--categories", "-c", action="store_true", help="List all categories")
    parser.add_argument("--show", "-s", help="Show keywords for a category")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.categories:
        show_categories()
    elif args.show:
        show_category_keywords(args.show)
    elif args.text:
        test_classification(args.text)
    else:
        # Default: run some sample tests
        print("Running sample classification tests...")
        
        test_cases = [
            "FDA issues warning letter for GMP violations",
            "일탈 조사 및 CAPA 대응 방안",
            "무균 공정 밸리데이션 가이드라인 개정",
            "타정 공정 최적화 연구",
            "신약 개발 임상 3상 결과 발표"
        ]
        
        for text in test_cases:
            test_classification(text)
        
        print("\n" + "="*60)
        print("Use --interactive for interactive testing")
        print("Use --categories to see all categories")
