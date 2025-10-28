import cv2
import numpy as np
import pytesseract
import base64
import io
from PIL import Image
import os
from improved_ocr import ImprovedCheckOCR

class DebugCheckOCR(ImprovedCheckOCR):
    """Enhanced OCR processor with debugging capabilities and improved preprocessing."""
    
    def __init__(self, debug_dir="debug_images"):
        super().__init__()
        self.debug_dir = debug_dir
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
    
    def save_debug_image(self, img, filename):
        """Save debug image for inspection."""
        cv2.imwrite(os.path.join(self.debug_dir, filename), img)
        print(f"📸 Debug image saved: {filename}")
    
    def gentle_preprocess(self, gray):
        """More gentle preprocessing approach."""
        # Method 1: Simple adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )
        
        # Method 2: OTSU threshold
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 3: Simple threshold with median
        median_val = np.median(gray)
        _, simple = cv2.threshold(gray, median_val - 20, 255, cv2.THRESH_BINARY)
        
        return {
            'adaptive': adaptive,
            'otsu': otsu,
            'simple': simple,
            'original': gray
        }
    
    def test_ocr_on_methods(self, img_dict, roi_name="test"):
        """Test OCR on different preprocessing methods."""
        results = {}
        
        for method_name, img in img_dict.items():
            if img is None:
                continue
                
            # Save debug image
            self.save_debug_image(img, f"{roi_name}_{method_name}.png")
            
            # Test different OCR configurations
            ocr_configs = {
                'psm6': '--oem 3 --psm 6',  # Uniform block of text
                'psm7': '--oem 3 --psm 7',  # Single text line
                'psm8': '--oem 3 --psm 8',  # Single word
                'psm13': '--oem 3 --psm 13' # Raw line. Treat the image as a single text line
            }
            
            method_results = {}
            for config_name, config in ocr_configs.items():
                try:
                    text = pytesseract.image_to_string(img, config=config).strip()
                    method_results[config_name] = text
                    print(f"  {method_name}-{config_name}: '{text}'")
                except Exception as e:
                    method_results[config_name] = f"ERROR: {str(e)}"
            
            results[method_name] = method_results
        
        return results
    
    def extract_check_fields_debug(self, data_url: str):
        """Enhanced extraction with detailed debugging."""
        try:
            print("🔍 Starting DEBUG OCR processing...")
            
            # Convert and save original
            original = self.decode_data_url(data_url)
            self.save_debug_image(original, "01_original.png")
            img = original.copy()
            
            # Scale up if needed
            if max(img.shape[:2]) < 1200:
                scale = 1200.0 / max(img.shape[:2])
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                self.save_debug_image(img, "02_scaled.png")
                print(f"📏 Scaled image by {scale:.2f}x to {img.shape[1]}x{img.shape[0]}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            self.save_debug_image(gray, "03_grayscale.png")
            
            # Test if auto-deskewing helps or hurts
            deskewed = self.auto_deskew(gray.copy())
            self.save_debug_image(deskewed, "04_deskewed.png")
            
            # Apply different preprocessing methods
            print("\n🧪 Testing preprocessing methods...")
            gray_methods = self.gentle_preprocess(gray)
            deskew_methods = self.gentle_preprocess(deskewed)
            
            # Test full image OCR first
            print("\n📄 Full image OCR test:")
            full_results_gray = self.test_ocr_on_methods(gray_methods, "fullimage_gray")
            full_results_deskew = self.test_ocr_on_methods(deskew_methods, "fullimage_deskew")
            
            # ROI definitions
            ROIS = {
                "date": (0.75, 0.04, 0.22, 0.06),
                "payee": (0.15, 0.18, 0.45, 0.06),
                "amount_numeric": (0.65, 0.18, 0.30, 0.06),
                "amount_words": (0.05, 0.27, 0.90, 0.06),
                "memo": (0.15, 0.47, 0.45, 0.06),
            }
            
            # Test ROI extraction
            print("\n🎯 Testing ROI extraction...")
            roi_results = {}
            
            for field_name, roi_coords in ROIS.items():
                print(f"\n--- {field_name.upper()} ROI ---")
                
                # Extract ROI from both gray and deskewed
                roi_gray = self.crop_rel(gray, roi_coords)
                roi_deskew = self.crop_rel(deskewed, roi_coords)
                
                if roi_gray.size == 0 or roi_deskew.size == 0:
                    print(f"⚠️ Empty ROI for {field_name}")
                    continue
                
                self.save_debug_image(roi_gray, f"roi_{field_name}_gray.png")
                self.save_debug_image(roi_deskew, f"roi_{field_name}_deskew.png")
                
                # Test preprocessing on ROIs
                roi_gray_methods = self.gentle_preprocess(roi_gray)
                roi_deskew_methods = self.gentle_preprocess(roi_deskew)
                
                # Test OCR on different methods
                print(f"  Gray ROI results:")
                gray_roi_results = self.test_ocr_on_methods(roi_gray_methods, f"roi_{field_name}_gray")
                
                print(f"  Deskewed ROI results:")
                deskew_roi_results = self.test_ocr_on_methods(roi_deskew_methods, f"roi_{field_name}_deskew")
                
                roi_results[field_name] = {
                    'gray': gray_roi_results,
                    'deskewed': deskew_roi_results
                }
            
            # Find best results for each field
            print("\n🏆 Best results summary:")
            best_results = {}
            
            for field_name, field_results in roi_results.items():
                best_text = ""
                best_confidence = 0
                best_method = "none"
                
                for img_type, img_results in field_results.items():
                    for preprocess_method, ocr_results in img_results.items():
                        for ocr_config, text in ocr_results.items():
                            if text and not text.startswith("ERROR") and len(text.strip()) > len(best_text.strip()):
                                best_text = text.strip()
                                best_method = f"{img_type}_{preprocess_method}_{ocr_config}"
                
                best_results[field_name] = {
                    'text': best_text,
                    'method': best_method
                }
                print(f"  {field_name}: '{best_text}' (via {best_method})")
            
            return {
                "extraction_success": True,
                "payee_name": best_results.get('payee', {}).get('text', ''),
                "date": best_results.get('date', {}).get('text', ''),
                "amount": best_results.get('amount_numeric', {}).get('text', ''),
                "memo": best_results.get('memo', {}).get('text', ''),
                "raw_text": "Debug extraction - see individual fields",
                "debug_results": best_results,
                "full_image_results": {
                    'gray': full_results_gray,
                    'deskewed': full_results_deskew
                }
            }
            
        except Exception as e:
            print(f"💥 Debug extraction failed: {str(e)}")
            return {
                "extraction_success": False,
                "error": str(e),
                "payee_name": None,
                "date": None,
                "amount": None,
                "memo": "",
                "raw_text": ""
            }


# Test script
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        
        # Convert image to data URL
        with open(image_path, 'rb') as f:
            img_data = f.read()
            data_url = f"data:image/jpeg;base64,{base64.b64encode(img_data).decode()}"
        
        # Run debug extraction
        debug_ocr = DebugCheckOCR()
        results = debug_ocr.extract_check_fields_debug(data_url)
        
        print(f"\n📊 Final Results:")
        print(f"Success: {results['extraction_success']}")
        if results['extraction_success']:
            print(f"Date: {results['date']}")
            print(f"Payee: {results['payee_name']}")
            print(f"Amount: {results['amount']}")
            print(f"Memo: {results['memo']}")
        else:
            print(f"Error: {results.get('error', 'Unknown error')}")
        
        print(f"\n📁 Check the 'debug_images' folder for intermediate processing steps")
    
    else:
        print("Usage: python debug_ocr.py <image_path>")
