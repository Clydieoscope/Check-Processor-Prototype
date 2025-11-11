import cv2
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.roi_config import ROIConfigurator
from app.improved_ocr import ImprovedCheckOCR
import numpy as np

# You'll need to provide the path to your check image
check_image_path = input("Enter the path to your check image: ")

if not os.path.exists(check_image_path):
    print(f"Error: File not found at {check_image_path}")
    exit(1)

# Initialize
configurator = ROIConfigurator()
ocr = ImprovedCheckOCR()

# Visualize ROIs
print("\n📊 Visualizing ROI regions on check...")
overlay = configurator.visualize_rois(check_image_path, roi_config="user_check", save_path="roi_visualization.png")
print("✅ ROI visualization saved to: roi_visualization.png")
print("   Please open this image to see where the system is looking for each field.")

# Show the ROI coordinates
print("\n📍 Current ROI Coordinates (x, y, width, height):")
rois = configurator.get_roi_config("user_check")
for field, coords in rois.items():
    print(f"  {field}: {coords}")

# Try to extract from the image
print("\n🔍 Attempting OCR extraction...")

# Read image and convert to data URL format for testing
img = cv2.imread(check_image_path)
_, buffer = cv2.imencode('.jpg', img)
import base64
b64_string = base64.b64encode(buffer).decode('utf-8')
data_url = f"data:image/jpeg;base64,{b64_string}"

results = ocr.extract_check_fields(data_url)

print("\n📋 Extraction Results:")
print(f"  Success: {results['extraction_success']}")
print(f"  Payee: {results.get('payee_name')}")
print(f"  Date: {results.get('date')}")
print(f"  Amount: {results.get('amount')}")
print(f"  Memo: {results.get('memo')}")
print(f"  Routing Number: {results.get('routing_number')}")
print(f"  Account Number: {results.get('account_number')}")
print(f"  Check Number: {results.get('check_number')}")

if 'detailed_results' in results:
    print("\n📝 Raw OCR Text for each region:")
    details = results['detailed_results']
    if 'raw_date' in details:
        print(f"  Date region: '{details['raw_date']}'")
    if 'payee' in details:
        print(f"  Payee region: '{details['payee']}'")
    if 'raw_amount_numeric' in details:
        print(f"  Amount region: '{details['raw_amount_numeric']}'")
    if 'memo' in details:
        print(f"  Memo region: '{details['memo']}'")
    if 'routing_number' in details:
        print(f"  Routing region: '{details['routing_number']}'")
    if 'account_number' in details:
        print(f"  Account region: '{details['account_number']}'")
    if 'check_number' in details:
        print(f"  Check# region: '{details['check_number']}'")

print("\n💡 Next steps:")
print("  1. Open 'roi_visualization.png' to see where the system is looking")
print("  2. If the boxes are in the wrong place, we need to adjust the ROI coordinates")
print("  3. You can use an image editor to find the correct percentages")

