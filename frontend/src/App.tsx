import './App.css'
import Webcam from 'react-webcam'
import {useCallback, useRef, useState} from 'react'

function App() {
  const webRef = useRef<Webcam>(null)
  const [front, setFrontImg] = useState('')
  const [back, setBackImg] = useState('')
  const [selectedSide, setSelectedSide] = useState('front');
  const [ocrText, setOcrText] = useState('')
  const [structuredData, setStructuredData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const capture = useCallback(() => {
    const shot = webRef.current?.getScreenshot()
    if (!shot) return
    if (selectedSide === 'front') {
      setFrontImg(shot)
    } else {
      setBackImg(shot)
    }
  }, [selectedSide])

  const runOCR = useCallback(async () => {
    setError(null)
    setOcrText('')
    setStructuredData(null)
    setLoading(true)
    try {
      // Always use front image for OCR, regardless of selectedSide
      if (!front) {
        setError('No front image to process. Please capture the front of the check first.')
        setLoading(false)
        return
      }
      const res = await fetch('http://localhost:8000/ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageDataUrl: front }),
      })
      if (!res.ok) {
        throw new Error(`Server responded ${res.status}`)
      }
      const json = await res.json()
      setOcrText(json.raw_text || '')
      setStructuredData(json.structured_data)
      
      if (!json.success) {
        setError(json.error || 'LLM processing failed')
      }
    } catch (e: any) {
      setError(e.message || 'OCR failed')
    } finally {
      setLoading(false)
    }
  }, [front])

  return (
    <>
      <div className='main-container'>
        <h1>Check Upload</h1>
        
        <div className='content-row'>
          {/* Left side - Image Previews */}
          <div className='preview-panel'>
            <h2>Captured Images</h2>
            <div className='image-grid'>
              <div className='image-item'>
                <h3>Front</h3>
                <div className='img-container'>
                  <img className='check-img' src={front}/>
                </div>
              </div>
              
              <div className='image-item'>
                <h3>Back</h3>
                <div className='img-container'>
                  <img className='check-img' src={back}/>
                </div>
              </div>
            </div>
          </div>

          {/* Middle - Webcam and Controls */}
          <div className="camera-panel">
            <div className='webcam-container'>
              <Webcam
                ref={webRef}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: 'user' }}
              />
            </div>

            <div className='controls'>
              <button id='capture-btn' onClick={capture}>Capture Image</button>

              <div className='radio-group'>
                <label>
                  <input
                    type="radio"
                    name="side"
                    value="front"
                    checked={selectedSide === 'front'}
                    onChange={(e) => setSelectedSide(e.target.value as 'front')}
                  />
                  Front
                </label>

                <label>
                  <input
                    type="radio"
                    name="side"
                    value="back"
                    checked={selectedSide === 'back'}
                    onChange={(e) => setSelectedSide(e.target.value as 'back')}
                  />
                  Back
                </label>
              </div>
            </div>
          </div>

          {/* Right side - OCR Output */}
          <div className="ocr-panel">
            <h2>Check Information</h2>
            {error && <p className="error-message">{error}</p>}
            
            {structuredData && structuredData.extraction_success && (
              <div className="structured-data">
                <h3>Extracted Information:</h3>
                <div className="data-item">
                  <strong>Payee:</strong> {structuredData.payee_name || 'Not found'}
                </div>
                <div className="data-item">
                  <strong>Date:</strong> {structuredData.date || 'Not found'}
                </div>
                <div className="data-item">
                  <strong>Amount:</strong> {structuredData.amount || 'Not found'}
                </div>
                {structuredData.memo && (
                  <div className="data-item">
                    <strong>Memo:</strong> {structuredData.memo}
                  </div>
                )}
              </div>
            )}
            
            <div className="text-output">
              <h3>Raw OCR Text:</h3>
              <pre>{ocrText}</pre>
            </div>
            <button onClick={runOCR}>{loading ? 'Processing…' : 'Extract Text'}</button>
          </div>
        </div>
      </div>
    </>
  )
}

export default App
