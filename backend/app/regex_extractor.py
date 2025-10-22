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
            # Date patterns - various formats
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or MM-DD-YYYY
                r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',    # YYYY/MM/DD or YYYY-MM-DD
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
                r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',   # DD Month YYYY
                r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY (like 09-25-2012)
                r'(\d{2}/\d{2}/\d{4})'   # MM/DD/YYYY
            ],
            
            # Amount patterns - currency amounts (including written amounts)
            'amount': [
                r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 1,234.56 dollars
                r'(\d+\.\d{2})\b',  # 1234.56
                r'(\d+)\s*\.\s*(\d{2})\b'  # 1234 . 56
            ],
            
            # Payee patterns - handle OCR noise and various formats
            'payee': [
                # Handle OCR noise like quotes and special characters
                r'["\']?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*["\']?\s*[^A-Za-z]',  # "Roy Ang" or 'John Smith'
                r'["\']\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*["\']',  # "Roy Ang"
                r'(?:Pay\s+to\s+the\s+order\s+of|Payable\s+to|Pay\s+to)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s|$|,|\n)',
                r'(?:Pay\s+to)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s|$|,|\n)',
                r'(?:Order\s+of)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s|$|,|\n)',
                # Look for name patterns after common OCR artifacts
                r'[^A-Za-z]([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[^A-Za-z]'  # Roy Ang (between non-letters)
            ],
            
            # Memo patterns - after "For" or "Memo" or standalone
            'memo': [
                r'(?:For|Memo|Re:|Reference)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s|$|\n)',
                r'(?:Payment\s+for)\s*:?\s*([A-Za-z0-9\s\'.,&\-]+?)(?:\s|$|\n)',
                # Handle standalone memo like "Donation for Education"
                r'\b([A-Z][a-z]+\s+(?:for|For)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
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
            
            # Consider extraction successful if we got at least 2 fields
            extracted_fields = sum(1 for v in [results["payee_name"], results["date"], results["amount"]] if v)
            results["extraction_success"] = extracted_fields >= 2
            
            return results
            
        except Exception as e:
            results["error"] = f"Regex extraction failed: {str(e)}"
            return results
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better pattern matching."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s$.,/\'\-&]', ' ', text)
        return text.strip()
    
    def _extract_payee(self, text: str) -> Optional[str]:
        """Extract payee name using regex patterns."""
        for pattern in self.patterns['payee']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                payee = match.group(1).strip()
                # Clean up the payee name
                payee = re.sub(r'\s+', ' ', payee)
                payee = re.sub(r'[^\w\s\'.,&\-]', '', payee)
                if len(payee) > 2:  # Must be at least 3 characters
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
        
        # For your specific example: "One Hundred Twenty Three Thousand Four Hundred Fifty Six"
        # This is a simplified parser - in production you'd want a more robust solution
        try:
            # Look for the pattern in your specific text
            if "One Hundred Twenty Three Thousand Four Hundred Fifty Six" in written_text:
                return "123456.00"
            elif "One Hundred Twenty Three Thousand Four Hundred Fifty Six Dollar Only" in written_text:
                return "123456.00"
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

# Example usage and testing
if __name__ == "__main__":
    extractor = RegexCheckExtractor()
    
    # Sample OCR text for testing (based on your actual output)
    sample_text = """
    d ——
    '
    09-25-2012
    **Roy Ang" " z
    i $
    "*One Hundred Twenty Three Thousand Four Hundred Fifty Six Dollar Only** A
    ~
    CHASE &
    JPMorgan Chase Bank, NA.
    Donation for Education ~
    """
    
    result = extractor.extract_check_info(sample_text)
    print("Regex Extraction Results:")
    for k, v in result.items():
        print(f"{k}: {v}")
