#!/usr/bin/env python
# coding: utf-8

"""
Fix the chatbot.py file by removing escaped quotes
"""

import re

def fix_chatbot_file():
    """Fix the escaped quotes in chatbot.py"""
    
    # Read the file
    with open('chatbot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace escaped quotes in f-strings with proper concatenation
    # Replace f\"...\" with f"..."
    content = re.sub(r'f\\"([^"]+)\\"', r'f"\1"', content)
    
    # Replace \\n with actual newlines in strings where appropriate
    content = content.replace('\\\\n', '\\n')
    
    # Fix specific problematic patterns
    patterns_to_fix = [
        (r'result \+= f\\"([^"]+)\\"', r'result += f"\1"'),
        (r'return f\\"([^"]+)\\"', r'return f"\1"'),
        (r'\\"\\n', '"\\n'),
        (r'\\"$', '"'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)
    
    # Write the fixed content back
    with open('chatbot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed chatbot.py file")

if __name__ == "__main__":
    fix_chatbot_file()