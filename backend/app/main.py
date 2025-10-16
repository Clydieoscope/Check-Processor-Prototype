from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64, io
from PIL import Image, ImageOps
import pytesseract

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OCRPayload(BaseModel):
    imageDataUrl: str  # data URL from react-webcam getScreenshot()

def decode_data_url(data_url: str) -> Image.Image:
    header, b64data = data_url.split(",", 1)
    img_bytes = base64.b64decode(b64data)
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.grayscale(img)
    return img

@app.post("/ocr")
def ocr(payload: OCRPayload):
    img = decode_data_url(payload.imageDataUrl)
    text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
    return {"text": text}

# Run: uvicorn main:app --reload --port 8000
