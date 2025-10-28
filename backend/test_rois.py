#!/usr/bin/env python3
"""
Test script for visualizing and testing ROI configurations on check images.
Run this to see how well the ROIs match your check layout.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.improved_ocr import ImprovedCheckOCR
from app.roi_config import ROIConfigurator
import cv2
import base64

def test_roi_extraction(image_path):
    """Test ROI extraction on a check image."""
    print("🔍 Testing ROI extraction on your check...")
    
    # Initialize the OCR processor
    ocr = ImprovedCheckOCR()
    
    # Convert image to data URL format (simulating web upload)
    with open(image_path, 'rb') as f:
        img_data = f.read()
        data_url = f"data:image/jpeg;base64,{base64.b64encode(img_data).decode()}"
    
    # Extract check information
    try:
        results = ocr.extract_check_fields(data_url)
        
        print("\n📊 Extraction Results:")
        print("=" * 50)
        print(f"✅ Success: {results['extraction_success']}")
        print(f"📅 Date: {results['date']}")
        print(f"👤 Payee: {results['payee_name']}")
        print(f"💰 Amount: ${results['amount']}")
        print(f"📝 Memo: {results['memo']}")
        
        if 'detailed_results' in results:
            print(f"\n🔍 Raw Extracted Text:")
            print(f"  Date field: '{results['detailed_results'].get('raw_date', 'N/A')}'")
            print(f"  Payee field: '{results['detailed_results'].get('payee', 'N/A')}'")
            print(f"  Amount field: '{results['detailed_results'].get('raw_amount_numeric', 'N/A')}'")
            print(f"  Amount words: '{results['detailed_results'].get('amount_words', 'N/A')}'")
            print(f"  Memo field: '{results['detailed_results'].get('memo', 'N/A')}'")
        
        return results
        
    except Exception as e:
        print(f"❌ Error during extraction: {str(e)}")
        return None

def visualize_rois(image_path, output_path=None):
    """Visualize ROI boxes on the check image."""
    print("🎨 Creating ROI visualization...")
    
    configurator = ROIConfigurator()
    
    try:
        # Create visualization
        if output_path is None:
            output_path = image_path.replace('.', '_with_rois.')
        
        overlay = configurator.visualize_rois(image_path, "user_check", output_path)
        print(f"✅ ROI visualization saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error creating visualization: {str(e)}")
        return None

def print_current_rois():
    """Print the current ROI configuration."""
    print("\n📐 Current ROI Configuration:")
    print("=" * 50)
    configurator = ROIConfigurator()
    config = configurator.get_roi_config("user_check")
    
    for field, (x, y, w, h) in config.items():
        print(f"{field:15}: x={x:.2f}, y={y:.2f}, w={w:.2f}, h={h:.2f}")
        print(f"{'':15}  (top-left: {x:.0%}, {y:.0%}, size: {w:.0%} x {h:.0%})")

if __name__ == "__main__":
    print("🏦 Check ROI Configuration Tester")
    print("=" * 50)
    
    # Print current configuration
    print_current_rois()
    
    # Test with image if provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            sys.exit(1)
        
        print(f"\n🖼️  Testing with image: {image_path}")
        
        # Create visualization
        viz_path = visualize_rois(image_path)
        
        # Test extraction
        results = test_roi_extraction(image_path)
        
        print(f"\n🎯 Next steps:")
        print(f"  1. Check the visualization: {viz_path}")
        print(f"  2. If ROIs don't align well, adjust coordinates in improved_ocr.py")
        print(f"  3. Re-run this test to verify improvements")
        
    else:
        print(f"\n💡 Usage:")
        print(f"  python test_rois.py <path_to_check_image>")
        print(f"\n📝 Example:")
        print(f"  python test_rois.py sample_check.jpg")
