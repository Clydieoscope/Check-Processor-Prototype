import cv2
import numpy as np
import pytesseract
import re
from dateutil import parser as dateparser
import imutils
from PIL import Image
import io
import base64

class ImprovedCheckOCR:
    def __init__(self):
        """Initialize the improved OCR processor with advanced preprocessing."""
        pass
    
    def decode_data_url(self, data_url: str) -> np.ndarray:
        """Convert data URL to OpenCV image format."""
        header, b64data = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        
        # Convert to PIL Image first
        pil_img = Image.open(io.BytesIO(img_bytes))
        
        # Convert PIL to OpenCV format
        img_array = np.array(pil_img)
        
        # Convert RGB to BGR for OpenCV
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    def auto_deskew(self, gray):
        """Automatically deskew the image to straighten tilted checks."""
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh == 0))
        if coords.size == 0:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        rotated = imutils.rotate_bound(gray, angle)
        return rotated

    def clean_for_ocr(self, img):
        """Apply advanced preprocessing for better OCR results."""
        # Gentle denoise + adaptive threshold
        den = cv2.fastNlMeansDenoising(img, None, 15, 7, 21)
        th = cv2.adaptiveThreshold(den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 15)
        # Light morphology to close gaps in digits/letters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
        return th

    def crop_rel(self, img, rel_box):
        """Crop image using relative coordinates (0-1 range)."""
        H, W = img.shape[:2]
        x, y, w, h = rel_box
        x1, y1 = int(x*W), int(y*H)
        x2, y2 = int((x+w)*W), int((y+h)*H)
        return img[y1:y2, x1:x2]

    def ocr_text(self, img, psm=6, allow=None):
        """Perform OCR with optimized configuration."""
        config = f'--oem 3 --psm {psm}'
        if allow:
            config += f' -c tessedit_char_whitelist={allow}'
        return pytesseract.image_to_string(img, config=config).strip()

    def parse_amount(self, text):
        """Extract currency amount from text."""
        text = text.replace(',', '').replace('O', '0')
        m = re.search(r'(\d+\.\d{2}|\d+)', text)
        return m.group(1) if m else ''

    def parse_date(self, text):
        """Parse date with fuzzy matching."""
        try:
            dt = dateparser.parse(text, fuzzy=True, dayfirst=False)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            return ''

    def extract_check_fields(self, data_url: str):
        """Main pipeline to extract check information using improved OCR."""
        try:
            # Convert data URL to OpenCV image
            original = self.decode_data_url(data_url)
            img = original.copy()

            # Upscale if image is too small
            if max(img.shape[:2]) < 1200:
                scale = 1200.0 / max(img.shape[:2])
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Convert to grayscale and preprocess
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = self.auto_deskew(gray)
            proc = self.clean_for_ocr(gray)

            # Define regions of interest (adjust these based on your check layout)
            ROIS = {
                "date": (0.72, 0.07, 0.24, 0.08),      # top-right corner
                "payee": (0.12, 0.30, 0.75, 0.10),     # "Pay to the order of" line
                "amount_numeric": (0.72, 0.36, 0.24, 0.12),  # $ ####.## box
                "amount_words": (0.08, 0.43, 0.82, 0.10),    # amount in words
                "memo": (0.12, 0.55, 0.75, 0.08),      # memo line (optional)
            }

            results = {}

            # Extract DATE
            roi_date = self.crop_rel(proc, ROIS["date"])
            date_txt = self.ocr_text(roi_date, psm=7)
            results["raw_date"] = date_txt
            results["date"] = self.parse_date(date_txt)

            # Extract PAYEE
            roi_payee = self.crop_rel(proc, ROIS["payee"])
            payee_alt = cv2.threshold(roi_payee, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            payee_txt = self.ocr_text(payee_alt, psm=7)
            payee_txt = re.sub(r'[^A-Za-z0-9 \'.,&-]', '', payee_txt)
            results["payee"] = payee_txt.strip()

            # Extract AMOUNT (numeric)
            roi_amt_num = self.crop_rel(proc, ROIS["amount_numeric"])
            amt_num_txt = self.ocr_text(roi_amt_num, psm=7, allow="$0123456789.,")
            results["raw_amount_numeric"] = amt_num_txt
            results["amount"] = self.parse_amount(amt_num_txt)

            # Extract AMOUNT (in words)
            roi_amt_words = self.crop_rel(proc, ROIS["amount_words"])
            amt_words_txt = self.ocr_text(roi_amt_words, psm=7)
            amt_words_txt = re.sub(r'[^A-Za-z0-9 /-]', ' ', amt_words_txt)
            amt_words_txt = re.sub(r'\s+', ' ', amt_words_txt).strip()
            results["amount_words"] = amt_words_txt

            # Extract MEMO (optional)
            roi_memo = self.crop_rel(proc, ROIS["memo"])
            memo_txt = self.ocr_text(roi_memo, psm=7)
            memo_txt = re.sub(r'[^A-Za-z0-9 \'.,&-]', '', memo_txt)
            results["memo"] = memo_txt.strip()

            # Also get full image OCR for fallback
            full_text = pytesseract.image_to_string(gray, config='--oem 3 --psm 6')
            results["raw_text"] = full_text

            return {
                "extraction_success": True,
                "payee_name": results["payee"],
                "date": results["date"],
                "amount": results["amount"],
                "memo": results["memo"],
                "raw_text": results["raw_text"],
                "detailed_results": results
            }

        except Exception as e:
            # Fallback to simple OCR if advanced processing fails
            try:
                img = self.decode_data_url(data_url)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                fallback_text = pytesseract.image_to_string(gray, config='--oem 3 --psm 6')
                
                return {
                    "extraction_success": False,
                    "payee_name": None,
                    "date": None,
                    "amount": None,
                    "memo": "",
                    "raw_text": fallback_text,
                    "error": f"Advanced OCR failed, using fallback: {str(e)}"
                }
            except Exception as fallback_error:
                return {
                    "extraction_success": False,
                    "payee_name": None,
                    "date": None,
                    "amount": None,
                    "memo": "",
                    "raw_text": "",
                    "error": f"OCR completely failed: {str(fallback_error)}"
                }
