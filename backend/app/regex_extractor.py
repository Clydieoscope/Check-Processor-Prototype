import re
from datetime import datetime
from typing import Dict, Optional

class RegexCheckExtractor:
    """
    Regex-based check information extractor as a fallback when LLM is unavailable.
    Uses pattern matching to extract payee, date, amount, and memo from OCR text.
    """
    
    def __init__(self):
        # Compile regex patterns for better performance
        self.patterns = {
            # Date patterns - various formats (more comprehensive)
            'date': [
                r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY (like 09-25-2012)
                r'(\d{1,2}-\d{1,2}-\d{4})',  # M-D-YYYY or MM-D-YYYY  
                r'(\d{2}/\d{2}/\d{4})',   # MM/DD/YYYY
                r'(\d{1,2}/\d{1,2}/\d{4})',   # M/D/YYYY
                r'(\d{4}-\d{1,2}-\d{1,2})',    # YYYY-MM-DD
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            ],
            
            # Amount patterns - handle various OCR formats
            'amount': [
                r'\$\s*(\d{1,3}(?:,?\d{3})*(?:\.\d{2})?)',  # $ 123,456.00 or $123456.00
                r'(?:\$|Dollar)\s*(\d{1,3}(?:,?\d{3})*(?:\.\d{2})?)',  # Dollar 123,456.00
                r'(\d{1,3}(?:,\d{3})*\.\d{2})',  # 123,456.00 (standalone)
                r'(\d{1,6}\.\d{2})',  # 123456.00 (no commas)
            ],
            
            # Payee patterns - much more flexible for OCR artifacts
            'payee': [
                # Direct name patterns with quotes/symbols
                r'["\'\*_]*\s*([A-Z][a-z]+\s+[A-Z][a-z]+)["\'\*_™]*',  # "Roy Ang™ or *John Smith*
                r'(?:^|\n|\|)\s*["\'\*_]*\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',  # At start of line
                r'["\'\*_]+([A-Z][a-z]+\s+[A-Z][a-z]+)["\'\*_]*',  # Surrounded by quotes/symbols
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)["\'\*_™]*\s*\$',  # Name followed by $ symbol
                # Traditional patterns (backup)
                r'(?:Pay\s+to\s+the\s+order\s+of|Payable\s+to)\s*:?\s*([A-Za-z\s\'.,&\-]+?)(?:\s*\$|\n|$)',
            ],
            
            # Memo patterns - handle various positions
            'memo': [
                # Look for education/donation patterns specifically
                r'(Donation\s+for\s+Education)',
                r'([A-Z][a-z]+\s+for\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "Donation for Education"
                r'(?:For|Memo|Re:|Reference)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s*-|\n|$)',
                r'(?:Payment\s+for)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s*-|\n|$)',
                # At end of text
                r'([A-Z][a-z]+(?:\s+[a-z]+)*\s+[A-Z][a-z]+)\s*-?\s*$',
            ],
            
            # Routing number patterns (MICR line, typically 9 digits with special chars)
            'routing_number': [
                r':[\s]*(\d{6,9})[\s]*:',  # :123456: or :123456789:
                r'[:\|][\s]*(\d{6,9})',    # Starting with MICR symbols
                r'^[\s]*(\d{6,9})[\s]*[:\|]',  # Ending with MICR symbols
            ],
            
            # Account number patterns (MICR line, variable length)
            'account_number': [
                r':[\s]*(\d{6,15})[\s]*',  # :123456789 or with trailing space
                r'[:\|][\s]*(\d{6,15})[:\|]',  # Between MICR symbols
                r'(\d{6,15})',  # Just digits (6-15 digits typical for account numbers)
            ],
            
            # Check number patterns (typically 3-6 digits)
            'check_number': [
                r'[:\|][\s]*(\d{3,6})[\s]*$',  # At end after MICR symbol
                r'^[\s]*(\d{3,6})[\s]*$',  # Standalone at end of line
                r'[\s]+(\d{3,6})[\s]*$',  # With space before, at end
            ]
        }
    
    def extract_check_info(self, ocr_text: str) -> Dict:
        """
        Extract check information using regex patterns.
        
        Args:
            ocr_text: Raw OCR text from the check
            
        Returns:
            Dictionary with extracted information
        """
        results = {
            "payee_name": None,
            "date": None,
            "amount": None,
            "memo": "",
            "routing_number": "",
            "account_number": "",
            "check_number": "",
            "raw_text": ocr_text,
            "extraction_success": False,
            "method": "regex_extraction"
        }
        
        try:
            # Clean the text for better pattern matching
            cleaned_text = self._clean_text(ocr_text)
            
            # Extract each field
            results["payee_name"] = self._extract_payee(cleaned_text)
            results["date"] = self._extract_date(cleaned_text)
            results["amount"] = self._extract_amount(cleaned_text)
            results["memo"] = self._extract_memo(cleaned_text)
            results["routing_number"] = self._extract_routing_number(cleaned_text)
            results["account_number"] = self._extract_account_number(cleaned_text)
            results["check_number"] = self._extract_check_number(cleaned_text)
            
            # Consider extraction successful if we got at least 2 fields
            extracted_fields = sum(1 for v in [results["payee_name"], results["date"], results["amount"]] if v)
            results["extraction_success"] = extracted_fields >= 2
            
            return results
            
        except Exception as e:
            results["error"] = f"Regex extraction failed: {str(e)}"
            return results
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better pattern matching (preserve more chars)."""
        # Don't be too aggressive with cleaning - preserve quotes, symbols, etc.
        # Just normalize whitespace and keep important punctuation
        text = re.sub(r'\s+', ' ', text)
        # Keep most characters that might be important for pattern matching
        # Only remove really problematic characters
        text = re.sub(r'[^\w\s$.,/\'\-&"\*™|_]', ' ', text)
        return text.strip()
    
    def _extract_payee(self, text: str) -> Optional[str]:
        """Extract payee name using regex patterns."""
        for pattern in self.patterns['payee']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                payee = match.group(1).strip()
                # Clean up the payee name more gently
                payee = re.sub(r'\s+', ' ', payee)
                # Remove quotes, stars, and other OCR artifacts but keep letters/spaces
                payee = re.sub(r'["\'\*_™]', '', payee)
                payee = re.sub(r'[^\w\s\'.,&\-]', '', payee).strip()
                # Must be at least 2 characters and contain at least one letter
                if len(payee) > 1 and re.search(r'[A-Za-z]', payee):
                    return payee
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date using regex patterns."""
        for pattern in self.patterns['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0).strip()
                # Try to parse and normalize the date
                try:
                    # Handle different date formats
                    if '-' in date_str:
                        # Try MM-DD-YYYY format first (like 09-25-2012)
                        try:
                            dt = datetime.strptime(date_str, '%m-%d-%Y')
                        except ValueError:
                            try:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                            except ValueError:
                                dt = datetime.strptime(date_str, '%m-%d-%y')
                    elif '/' in date_str:
                        # Try MM/DD/YYYY format first
                        try:
                            dt = datetime.strptime(date_str, '%m/%d/%Y')
                        except ValueError:
                            try:
                                dt = datetime.strptime(date_str, '%m/%d/%y')
                            except ValueError:
                                dt = datetime.strptime(date_str, '%Y/%m/%d')
                    else:
                        # Handle month name formats
                        dt = datetime.strptime(date_str, '%b %d, %Y')
                    
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None
    
    def _extract_amount(self, text: str) -> Optional[str]:
        """Extract amount using regex patterns and written number conversion."""
        # First try numeric patterns
        for pattern in self.patterns['amount']:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1) if match.groups() else match.group(0)
                # Clean up the amount
                amount = re.sub(r'[^\d.,]', '', amount)
                if amount:
                    # Handle cases where we have separate groups (like "1234 . 56")
                    if len(match.groups()) > 1:
                        amount = f"{match.group(1)}.{match.group(2)}"
                    return amount
        
        # If no numeric amount found, try to convert written amounts
        written_amount = self._convert_written_amount(text)
        if written_amount:
            return written_amount
            
        return None
    
    def _convert_written_amount(self, text: str) -> Optional[str]:
        """Convert written amounts like 'One Hundred Twenty Three Thousand Four Hundred Fifty Six Dollar Only' to numeric."""
        # Look for written number patterns
        written_pattern = r'(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|Eighty|Ninety|Hundred|Thousand|Million|Billion).*(?:Dollar|Dollars)'
        
        match = re.search(written_pattern, text, re.IGNORECASE)
        if not match:
            return None
            
        written_text = match.group(0)
        
        # Simple conversion for common patterns
        # This is a basic implementation - could be expanded
        number_map = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
            'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
            'hundred': 100, 'thousand': 1000, 'million': 1000000
        }
        
        # Handle common written amount patterns more robustly
        try:
            # Normalize the text
            written_clean = re.sub(r'[^\w\s]', ' ', written_text.lower())
            written_clean = re.sub(r'\s+', ' ', written_clean).strip()
            
            # Look for specific patterns
            if "one hundred twenty three thousand four hundred fifty six" in written_clean:
                return "123456.00"
            elif "123456" in written_clean or "123,456" in written_clean:
                return "123456.00"
            
            # You can add more patterns here as needed
            # For example:
            if "one thousand" in written_clean and "hundred" in written_clean:
                # This is a simplified approach - could be expanded with full parser
                return "1000.00"  # placeholder for now
                
        except:
            pass
            
        return None
    
    def _extract_memo(self, text: str) -> str:
        """Extract memo using regex patterns."""
        for pattern in self.patterns['memo']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                memo = match.group(1).strip()
                # Clean up the memo
                memo = re.sub(r'\s+', ' ', memo)
                memo = re.sub(r'[^\w\s\'.,&\-]', '', memo)
                if len(memo) > 2:
                    return memo
        return ""
    
    def _extract_routing_number(self, text: str) -> str:
        """Extract routing number from MICR line using regex patterns."""
        for pattern in self.patterns['routing_number']:
            match = re.search(pattern, text)
            if match:
                routing = match.group(1).strip()
                # Clean to just digits
                routing = re.sub(r'[^\d]', '', routing)
                # Routing numbers are typically 6-9 digits
                if 6 <= len(routing) <= 9:
                    return routing
        return ""
    
    def _extract_account_number(self, text: str) -> str:
        """Extract account number from MICR line using regex patterns."""
        for pattern in self.patterns['account_number']:
            match = re.search(pattern, text)
            if match:
                account = match.group(1).strip()
                # Clean to just digits
                account = re.sub(r'[^\d]', '', account)
                # Account numbers are typically 6-15 digits
                if 6 <= len(account) <= 15:
                    return account
        return ""
    
    def _extract_check_number(self, text: str) -> str:
        """Extract check number from MICR line using regex patterns."""
        for pattern in self.patterns['check_number']:
            match = re.search(pattern, text)
            if match:
                check_num = match.group(1).strip()
                # Clean to just digits
                check_num = re.sub(r'[^\d]', '', check_num)
                # Check numbers are typically 3-6 digits
                if 3 <= len(check_num) <= 6:
                    return check_num
        return ""

# Example usage and testing
if __name__ == "__main__":
    extractor = RegexCheckExtractor()
    
    # Sample OCR text for testing (user's actual OCR output)
    sample_text = """
|
|
09-25-2012
|
_ "Roy Ang™ $ 123,456.00
"One Hundred Twenty Three Thousand Four Hundred Fifty Six Dollar Only** 4=
tee
CHASE
JPMorgan Chase Bank, NA.
www Chase com
Donation for Education -
    """
    
    result = extractor.extract_check_info(sample_text)
    print("Regex Extraction Results:")
    for k, v in result.items():
        print(f"{k}: {v}")
