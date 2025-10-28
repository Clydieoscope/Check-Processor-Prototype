import cv2
import numpy as np
import base64
import io
from PIL import Image

class ROIConfigurator:
    def __init__(self):
        """Tool for visualizing and configuring ROIs for check OCR."""
        
        # Default ROI configurations for different check types
        self.roi_presets = {
            "user_check": {
                "date": (0.75, 0.04, 0.22, 0.06),      # top-right corner (09-25-2012)
                "payee": (0.15, 0.18, 0.45, 0.06),     # "Pay to the order of" line (**Roy Ang**)
                "amount_numeric": (0.65, 0.18, 0.30, 0.06),  # $ amount box (**123,456.00**)
                "amount_words": (0.05, 0.27, 0.90, 0.06),    # amount in words (One Hundred Twenty...)
                "memo": (0.15, 0.47, 0.45, 0.06),      # memo line (Donation for Education)
            },
            "standard": {
                "date": (0.72, 0.07, 0.24, 0.08),
                "payee": (0.12, 0.30, 0.75, 0.10),
                "amount_numeric": (0.72, 0.36, 0.24, 0.12),
                "amount_words": (0.08, 0.43, 0.82, 0.10),
                "memo": (0.12, 0.55, 0.75, 0.08),
            },
            "business_check": {
                "date": (0.70, 0.05, 0.26, 0.10),
                "payee": (0.10, 0.28, 0.80, 0.12),
                "amount_numeric": (0.70, 0.34, 0.26, 0.14),
                "amount_words": (0.06, 0.41, 0.85, 0.12),
                "memo": (0.10, 0.53, 0.80, 0.10),
            },
            "personal_check": {
                "date": (0.74, 0.09, 0.22, 0.06),
                "payee": (0.14, 0.32, 0.70, 0.08),
                "amount_numeric": (0.74, 0.38, 0.22, 0.10),
                "amount_words": (0.10, 0.45, 0.78, 0.08),
                "memo": (0.14, 0.57, 0.70, 0.06),
            }
        }
    
    def decode_data_url(self, data_url: str) -> np.ndarray:
        """Convert data URL to OpenCV image format."""
        header, b64data = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        pil_img = Image.open(io.BytesIO(img_bytes))
        img_array = np.array(pil_img)
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return img_array
    
    def visualize_rois(self, image_path_or_dataurl, roi_config="standard", save_path=None):
        """Visualize ROIs on a check image."""
        if image_path_or_dataurl.startswith('data:'):
            img = self.decode_data_url(image_path_or_dataurl)
        else:
            img = cv2.imread(image_path_or_dataurl)
        
        if img is None:
            raise ValueError("Could not load image")
        
        # Get ROI configuration
        rois = self.roi_presets.get(roi_config, self.roi_presets["standard"])
        
        # Draw ROIs on image
        H, W = img.shape[:2]
        colors = {
            "date": (0, 255, 0),        # Green
            "payee": (255, 0, 0),       # Blue
            "amount_numeric": (0, 0, 255),  # Red
            "amount_words": (255, 255, 0),  # Cyan
            "memo": (255, 0, 255),      # Magenta
        }
        
        overlay = img.copy()
        
        for field, (x, y, w, h) in rois.items():
            # Convert relative coordinates to absolute
            x1, y1 = int(x * W), int(y * H)
            x2, y2 = int((x + w) * W), int((y + h) * H)
            
            # Draw rectangle
            color = colors.get(field, (255, 255, 255))
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            
            # Add label
            label = field.replace('_', ' ').title()
            cv2.putText(overlay, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        if save_path:
            cv2.imwrite(save_path, overlay)
            print(f"ROI visualization saved to: {save_path}")
        
        return overlay
    
    def create_custom_rois(self, image_path_or_dataurl):
        """Interactive ROI creation (requires GUI - for local development)."""
        print("Custom ROI Configuration:")
        print("Use these coordinates as (x, y, width, height) in decimal format (0-1)")
        print("Example: date field at top-right might be (0.72, 0.07, 0.24, 0.08)")
        print("\nCurrent presets available:")
        for preset_name in self.roi_presets.keys():
            print(f"  - {preset_name}")
    
    def get_roi_config(self, preset="standard"):
        """Get ROI configuration for a specific preset."""
        return self.roi_presets.get(preset, self.roi_presets["standard"])
    
    def update_roi_config(self, preset, field, coordinates):
        """Update ROI configuration for a field."""
        if preset not in self.roi_presets:
            self.roi_presets[preset] = {}
        self.roi_presets[preset][field] = coordinates
        print(f"Updated {field} ROI for {preset} preset: {coordinates}")


# Example usage:
if __name__ == "__main__":
    configurator = ROIConfigurator()
    
    # Print current configurations
    print("Available ROI Presets:")
    for preset_name, config in configurator.roi_presets.items():
        print(f"\n{preset_name.upper()}:")
        for field, coords in config.items():
            print(f"  {field}: {coords}")
