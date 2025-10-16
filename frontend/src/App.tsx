import './App.css'
import Webcam from 'react-webcam'
import {useCallback, useRef, useState} from 'react'

function App() {
  const webRef = useRef<Webcam>(null)
  const [front, setFrontImg] = useState('')
  const [back, setBackImg] = useState('')
  const [selectedSide, setSelectedSide] = useState('front');
  const [ocrText, setOcrText] = useState('')
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
    setLoading(true)
    try {
      const dataUrl = selectedSide === 'front' ? front : back
      if (!dataUrl) {
        setError(`No ${selectedSide} image to process.`)
        setLoading(false)
        return
      }
      const res = await fetch('http://localhost:8000/ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageDataUrl: dataUrl }),
      })
      if (!res.ok) {
        throw new Error(`Server responded ${res.status}`)
      }
      const json: { text: string } = await res.json()
      setOcrText(json.text || '')
    } catch (e: any) {
      setError(e.message || 'OCR failed')
    } finally {
      setLoading(false)
    }
  }, [selectedSide, front, back])

  return (
    <>
      <div className='Container'>
        <div className='row'>
          <div className="col">
        <h1>Check Upload</h1>
          <div className='webcam-container'>
            <Webcam
              ref={webRef}
              screenshotFormat="image/jpeg"
              videoConstraints={{ facingMode: 'user' }}
            />
          </div>

          <div className='flex'>
          <button id='capture-btn' onClick={capture}>Capture Image</button>

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

        <div className='preview-pane col'>
          <h2>Preview</h2>
          <div>
            <h3>Front</h3>
            <div className='img-container'>
              <img className='check-img' id='front' src={front}/>
            </div>
          </div>
          
          <div>
            <h3>Back</h3>
            <div className='img-container'>
              <img className='check-img' id='back' src={back}/>
            </div>
          </div>
          <div>
            <button onClick={runOCR}>{loading ? 'Processing…' : 'Extract Text'}</button>
          </div>
        </div>

        </div>
        
        
      </div>

      <div className="ocr-output">
        <h2>OCR Result ({selectedSide})</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <pre style={{ whiteSpace: 'pre-wrap' }}>{ocrText}</pre>
      </div>      
    </>
  )
}

export default App
