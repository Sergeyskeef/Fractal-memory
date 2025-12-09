#!/usr/bin/env python3
"""Analyze audit report and extract non-import issues."""

import re
from pathlib import Path

def analyze_report(report_path):
    """Extract and categorize issues from audit report."""
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Split into issues
    issues = content.split('### 🟠 [HIGH]')
    issues.extend(content.split('### 🟡 [MEDIUM]'))
    issues.extend(content.split('### 🟢 [LOW]'))
    
    # Categorize
    by_category = {
        'schema': [],
        'memory': [],
        'retrieval': [],
        'learning': [],
        'api': [],
        'imports': []
    }
    
    for issue in issues:
        if '**Category:**' not in issue:
            continue
        
        # Extract category
        match = re.search(r'\*\*Category:\*\* (\w+)', issue)
        if match:
            category = match.group(1)
            if category in by_category:
                by_category[category].append(issue)
    
    # Print summary
    print("=" * 80)
    print("AUDIT REPORT ANALYSIS")
    print("=" * 80)
    print()
    
    for category, items in by_category.items():
        if category != 'imports' and items:
            print(f"\n{'='*80}")
            print(f"{category.upper()} ISSUES: {len(items)}")
            print('='*80)
            
            for i, issue in enumerate(items[:5], 1):  # Show first 5
                print(f"\n--- Issue {i} ---")
                # Extract title
                title_match = re.search(r'### [🟠🟡🟢] \[.*?\] (.+)', issue)
                if title_match:
                    print(f"Title: {title_match.group(1)}")
                
                # Extract location
                loc_match = re.search(r'\*\*Location:\*\* `(.+?)`', issue)
                if loc_match:
                    print(f"Location: {loc_match.group(1)}")
                
                # Extract description
                desc_match = re.search(r'\*\*Description:\*\* (.+)', issue)
                if desc_match:
                    print(f"Description: {desc_match.group(1)}")
                
                print()
    
    print(f"\n{'='*80}")
    print(f"IMPORTS ISSUES: {len(by_category['imports'])} (mostly node_modules)")
    print('='*80)

if __name__ == '__main__':
    report_dir = Path('audit_reports')
    latest_report = sorted(report_dir.glob('audit_report_*.md'))[-1]
    print(f"Analyzing: {latest_report}\n")
    analyze_report(latest_report)
