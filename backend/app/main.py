from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64, io
from PIL import Image, ImageOps
import pytesseract
import sys
import os
import logging
sys.path.append(os.path.dirname(__file__))
from llm_service import CheckProcessorLLM
from improved_ocr import ImprovedCheckOCR
from regex_extractor import RegexCheckExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the services
improved_ocr = ImprovedCheckOCR()
regex_extractor = RegexCheckExtractor()

# Check if OpenAI API key is available
try:
    llm_service = CheckProcessorLLM()
    llm_available = True
    logger.info("✅ LLM service initialized successfully")
except Exception as e:
    llm_service = None
    llm_available = False
    logger.warning(f"⚠️ LLM service unavailable: {str(e)}")

class OCRPayload(BaseModel):
    imageDataUrl: str  # data URL from react-webcam getScreenshot()

def decode_data_url(data_url: str) -> Image.Image:
    header, b64data = data_url.split(",", 1)
    img_bytes = base64.b64decode(b64data)
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.grayscale(img)
    return img

@app.post("/visualize_rois")
def visualize_rois(payload: OCRPayload):
    """Visualize ROI regions on the check image for debugging."""
    try:
        from roi_config import ROIConfigurator
        import cv2
        import numpy as np
        
        configurator = ROIConfigurator()
        
        # Decode the image
        img = decode_data_url(payload.imageDataUrl)
        img_array = np.array(img)
        if len(img_array.shape) == 2:  # Grayscale
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        else:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Get ROI visualization
        overlay = configurator.visualize_rois(payload.imageDataUrl, roi_config="user_check")
        
        # Convert back to base64
        _, buffer = cv2.imencode('.jpg', overlay)
        b64_string = base64.b64encode(buffer).decode('utf-8')
        viz_data_url = f"data:image/jpeg;base64,{b64_string}"
        
        return {
            "success": True,
            "visualization": viz_data_url,
            "rois": configurator.get_roi_config("user_check")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/ocr")
def ocr(payload: OCRPayload):
    logger.info("🔍 Starting smart OCR processing with fallback system...")
    
    # Step 1: Try improved OCR with region detection
    try:
        logger.info("📸 Attempting improved OCR with region detection...")
        improved_results = improved_ocr.extract_check_fields(payload.imageDataUrl)
        logger.info(f"✅ Improved OCR completed. Success: {improved_results['extraction_success']}")
        
        if improved_results["extraction_success"]:
            logger.info("🎯 Improved OCR succeeded!")
            
            # Step 2: Try LLM validation (if available)
            if llm_available and llm_service:
                try:
                    logger.info("🤖 Attempting LLM validation...")
                    llm_results = llm_service.process_check_text(improved_results["raw_text"])
                    logger.info("✅ LLM processing completed successfully")
                    logger.info(f"📊 LLM Results: payee={llm_results.get('payee_name')}, date={llm_results.get('date')}, amount={llm_results.get('amount')}")
                    
                    # Check if LLM actually extracted useful data
                    llm_extracted_fields = sum(1 for v in [llm_results.get('payee_name'), llm_results.get('date'), llm_results.get('amount')] if v)
                    improved_extracted_fields = sum(1 for v in [improved_results["payee_name"], improved_results["date"], improved_results["amount"]] if v)
                    
                    logger.info(f"📈 Field extraction: Improved OCR={improved_extracted_fields}, LLM={llm_extracted_fields}")
                    
                    # If LLM extracted more fields than improved OCR, use LLM results
                    if llm_extracted_fields > improved_extracted_fields:
                        logger.info("🎯 LLM extracted more fields, using LLM results...")
                        return {
                            "raw_text": improved_results["raw_text"],
                            "structured_data": {
                                "payee_name": llm_results.get("payee_name"),
                                "date": llm_results.get("date"),
                                "amount": llm_results.get("amount"),
                                "memo": llm_results.get("memo", ""),
                                "routing_number": improved_results.get("routing_number", ""),
                                "account_number": improved_results.get("account_number", ""),
                                "check_number": improved_results.get("check_number", ""),
                                "raw_text": improved_results["raw_text"],
                                "extraction_success": True,
                                "method": "improved_ocr + llm"
                            },
                            "success": True,
                            "debug_info": {
                                "improved_ocr_success": True,
                                "llm_success": True,
                                "llm_available": True,
                                "method_used": "improved_ocr + llm_validation"
                            }
                        }
                    else:
                        logger.info("🔄 LLM didn't extract more fields, trying regex extraction...")
                        # Try regex extraction as a middle layer
                        try:
                            logger.info("🔍 Attempting regex-based extraction...")
                            regex_results = regex_extractor.extract_check_info(improved_results["raw_text"])
                            logger.info(f"✅ Regex extraction completed. Success: {regex_results['extraction_success']}")
                            
                            if regex_results["extraction_success"]:
                                logger.info("🎯 Regex extraction succeeded!")
                                return {
                                    "raw_text": regex_results["raw_text"],
                                    "structured_data": regex_results,
                                    "success": True,
                                    "debug_info": {
                                        "improved_ocr_success": True,
                                        "llm_success": True,
                                        "regex_success": True,
                                        "llm_available": True,
                                        "method_used": "improved_ocr + regex"
                                    }
                                }
                        except Exception as regex_error:
                            logger.warning(f"⚠️ Regex extraction failed: {str(regex_error)}")
                        
                        # Fall back to improved OCR results
                        logger.info("🔄 Using improved OCR results...")
                        return {
                            "raw_text": improved_results["raw_text"],
                            "structured_data": {
                                "payee_name": improved_results["payee_name"],
                                "date": improved_results["date"],
                                "amount": improved_results["amount"],
                                "memo": improved_results["memo"],
                                "routing_number": improved_results.get("routing_number", ""),
                                "account_number": improved_results.get("account_number", ""),
                                "check_number": improved_results.get("check_number", ""),
                                "raw_text": improved_results["raw_text"],
                                "extraction_success": True,
                                "method": "improved_ocr_only"
                            },
                            "success": True,
                            "debug_info": {
                                "improved_ocr_success": True,
                                "llm_success": True,
                                "llm_available": True,
                                "method_used": "improved_ocr_only"
                            }
                        }
                        
                except Exception as llm_error:
                    logger.warning(f"⚠️ LLM processing failed: {str(llm_error)}")
                    logger.info("🔄 Falling back to regex extraction...")
                    
                    # Try regex extraction when LLM fails
                    try:
                        logger.info("🔍 Attempting regex-based extraction...")
                        regex_results = regex_extractor.extract_check_info(improved_results["raw_text"])
                        logger.info(f"✅ Regex extraction completed. Success: {regex_results['extraction_success']}")
                        
                        if regex_results["extraction_success"]:
                            logger.info("🎯 Regex extraction succeeded!")
                            return {
                                "raw_text": regex_results["raw_text"],
                                "structured_data": regex_results,
                                "success": True,
                                "debug_info": {
                                    "improved_ocr_success": True,
                                    "llm_success": False,
                                    "regex_success": True,
                                    "llm_available": True,
                                    "llm_error": str(llm_error),
                                    "method_used": "improved_ocr + regex"
                                }
                            }
                    except Exception as regex_error:
                        logger.warning(f"⚠️ Regex extraction failed: {str(regex_error)}")
                    
                    # Final fallback to improved OCR results
                    logger.info("🔄 Using improved OCR results only...")
                    return {
                        "raw_text": improved_results["raw_text"],
                        "structured_data": {
                            "payee_name": improved_results["payee_name"],
                            "date": improved_results["date"],
                            "amount": improved_results["amount"],
                            "memo": improved_results["memo"],
                            "routing_number": improved_results.get("routing_number", ""),
                            "account_number": improved_results.get("account_number", ""),
                            "check_number": improved_results.get("check_number", ""),
                            "raw_text": improved_results["raw_text"],
                            "extraction_success": True,
                            "method": "improved_ocr_only"
                        },
                        "success": True,
                        "debug_info": {
                            "improved_ocr_success": True,
                            "llm_success": False,
                            "llm_available": True,
                            "llm_error": str(llm_error),
                            "method_used": "improved_ocr_only"
                        }
                    }
            else:
                logger.info("ℹ️ LLM not available, using improved OCR results...")
                return {
                    "raw_text": improved_results["raw_text"],
                    "structured_data": {
                        "payee_name": improved_results["payee_name"],
                        "date": improved_results["date"],
                        "amount": improved_results["amount"],
                        "memo": improved_results["memo"],
                        "routing_number": improved_results.get("routing_number", ""),
                        "account_number": improved_results.get("account_number", ""),
                        "check_number": improved_results.get("check_number", ""),
                        "raw_text": improved_results["raw_text"],
                        "extraction_success": True,
                        "method": "improved_ocr_only"
                    },
                    "success": True,
                    "debug_info": {
                        "improved_ocr_success": True,
                        "llm_success": False,
                        "llm_available": False,
                        "method_used": "improved_ocr_only"
                    }
                }
        else:
            logger.warning("⚠️ Improved OCR failed, trying regex extraction...")
            logger.info(f"❌ Improved OCR error: {improved_results.get('error', 'Unknown error')}")
            
            # Step 3: Try regex extraction on the raw text
            try:
                logger.info("🔍 Attempting regex-based extraction...")
                regex_results = regex_extractor.extract_check_info(improved_results["raw_text"])
                logger.info(f"✅ Regex extraction completed. Success: {regex_results['extraction_success']}")
                
                if regex_results["extraction_success"]:
                    logger.info("🎯 Regex extraction succeeded!")
                    return {
                        "raw_text": regex_results["raw_text"],
                        "structured_data": regex_results,
                        "success": True,
                        "debug_info": {
                            "improved_ocr_success": False,
                            "regex_success": True,
                            "llm_available": llm_available,
                            "method_used": "regex_extraction"
                        }
                    }
                else:
                    logger.warning("⚠️ Regex extraction failed, trying simple OCR...")
                    
            except Exception as regex_error:
                logger.warning(f"⚠️ Regex extraction failed: {str(regex_error)}")
            
            # Step 4: Fallback to simple OCR
            logger.info("📝 Falling back to simple OCR...")
            img = decode_data_url(payload.imageDataUrl)
            ocr_text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
            
            # Try regex on simple OCR text
            try:
                logger.info("🔍 Attempting regex extraction on simple OCR text...")
                regex_results = regex_extractor.extract_check_info(ocr_text)
                if regex_results["extraction_success"]:
                    logger.info("✅ Regex extraction on simple OCR succeeded!")
                    return {
                        "raw_text": ocr_text,
                        "structured_data": regex_results,
                        "success": True,
                        "debug_info": {
                            "improved_ocr_success": False,
                            "regex_success": True,
                            "llm_available": llm_available,
                            "method_used": "simple_ocr + regex"
                        }
                    }
            except Exception as regex_error:
                logger.warning(f"⚠️ Regex extraction on simple OCR failed: {str(regex_error)}")
            
            # Final fallback: return raw OCR text
            logger.info("📄 Returning raw OCR text as final fallback...")
            return {
                "raw_text": ocr_text,
                "structured_data": {
                    "payee_name": None,
                    "date": None,
                    "amount": None,
                    "memo": "",
                    "routing_number": "",
                    "account_number": "",
                    "check_number": "",
                    "raw_text": ocr_text,
                    "extraction_success": False,
                    "method": "raw_ocr_only"
                },
                "success": True,
                "debug_info": {
                    "improved_ocr_success": False,
                    "regex_success": False,
                    "llm_available": llm_available,
                    "method_used": "raw_ocr_only"
                }
            }
            
    except Exception as e:
        logger.error(f"💥 Complete OCR pipeline failure: {str(e)}")
        return {
            "raw_text": "",
            "structured_data": None,
            "success": False,
            "error": f"All OCR methods failed: {str(e)}",
            "debug_info": {
                "improved_ocr_success": False,
                "regex_success": False,
                "llm_available": llm_available,
                "complete_failure": True,
                "final_error": str(e)
            }
        }

# Run: uvicorn main:app --reload --port 8000
