#!/usr/bin/env python3
"""
Test script to verify regex extraction works with the user's actual OCR text.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.regex_extractor import RegexCheckExtractor

def test_user_ocr_text():
    """Test regex extraction with the user's actual OCR output."""
    
    # User's actual OCR text
    user_ocr_text = """|
|
09-25-2012
|
_ "Roy Ang™ $ 123,456.00
"One Hundred Twenty Three Thousand Four Hundred Fifty Six Dollar Only** 4=
tee
CHASE
JPMorgan Chase Bank, NA.
www Chase com
Donation for Education -"""
    
    print("🧪 Testing Regex Extraction")
    print("=" * 50)
    print("Input OCR Text:")
    print(repr(user_ocr_text))
    print("\n" + "=" * 50)
    
    # Initialize extractor
    extractor = RegexCheckExtractor()
    
    # Extract information
    results = extractor.extract_check_info(user_ocr_text)
    
    print("📊 Extraction Results:")
    print("=" * 50)
    for key, value in results.items():
        if key != 'raw_text':  # Skip raw text to keep output clean
            print(f"  {key}: {value}")
    
    print("\n🎯 Expected vs Actual:")
    print("=" * 50)
    expected = {
        'date': '2012-09-25',
        'payee_name': 'Roy Ang',
        'amount': '123456.00',
        'memo': 'Donation for Education'
    }
    
    for field, expected_value in expected.items():
        actual_value = results.get(field)
        status = "✅" if actual_value == expected_value else "❌"
        print(f"  {status} {field}: expected='{expected_value}', actual='{actual_value}'")
    
    print(f"\n📈 Overall Success: {results.get('extraction_success', False)}")
    
    return results

if __name__ == "__main__":
    test_user_ocr_text()
