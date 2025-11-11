import './App.css'
import Webcam from 'react-webcam'
import {useCallback, useRef, useState, useEffect} from 'react'

function App() {
  const webRef = useRef<Webcam>(null)
  const [front, setFrontImg] = useState('')
  const [back, setBackImg] = useState('')
  const [selectedSide, setSelectedSide] = useState('front');
  const [ocrText, setOcrText] = useState('')
  const [structuredData, setStructuredData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [roiVisualization, setRoiVisualization] = useState<string | null>(null)
  const [showDebug, setShowDebug] = useState(false)
  const [showOverlay, setShowOverlay] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)

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

  const visualizeROIs = useCallback(async () => {
    if (!front) {
      setError('No front image to visualize. Please capture the front of the check first.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/visualize_rois', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageDataUrl: front }),
      })
      if (!res.ok) {
        throw new Error(`Server responded ${res.status}`)
      }
      const json = await res.json()
      if (json.success) {
        setRoiVisualization(json.visualization)
        setShowDebug(true)
      } else {
        setError(json.error || 'ROI visualization failed')
      }
    } catch (e: any) {
      setError(e.message || 'Visualization failed')
    } finally {
      setLoading(false)
    }
  }, [front])

  // Draw ROI overlay on canvas
  useEffect(() => {
    if (!showOverlay || !canvasRef.current || !webRef.current) return

    const canvas = canvasRef.current
    const video = webRef.current.video

    if (!video) return

    // Set canvas size to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // ROI coordinates (matching backend user_check preset)
    const rois = {
      date: { x: 0.76, y: 0.35, w: 0.20, h: 0.08, color: '#00ff00', label: 'Date' },
      payee: { x: 0.05, y: 0.24, w: 0.65, h: 0.08, color: '#ff0000', label: 'Payee' },
      amount_numeric: { x: 0.76, y: 0.43, w: 0.20, h: 0.08, color: '#0000ff', label: 'Amount' },
      amount_words: { x: 0.05, y: 0.52, w: 0.80, h: 0.10, color: '#00ffff', label: 'Amount Words' },
      memo: { x: 0.12, y: 0.64, w: 0.50, h: 0.09, color: '#ff00ff', label: 'Memo' },
      routing_number: { x: 0.07, y: 0.73, w: 0.15, h: 0.10, color: '#ffff00', label: 'Routing' },
      account_number: { x: 0.22, y: 0.73, w: 0.18, h: 0.10, color: '#ff8800', label: 'Account' },
      check_number: { x: 0.40, y: 0.73, w: 0.10, h: 0.10, color: '#8800ff', label: 'Check#' }
    }

    const drawOverlay = () => {
      if (!showOverlay) return

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      Object.entries(rois).forEach(([name, roi]) => {
        const x1 = roi.x * canvas.width
        const y1 = roi.y * canvas.height
        const x2 = (roi.x + roi.w) * canvas.width
        const y2 = (roi.y + roi.h) * canvas.height

        // Draw semi-transparent rectangle
        ctx.strokeStyle = roi.color
        ctx.lineWidth = 3
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

        // Draw label background
        ctx.fillStyle = roi.color
        ctx.globalAlpha = 0.7
        ctx.fillRect(x1, y1 - 20, ctx.measureText(roi.label).width + 10, 20)

        // Draw label text
        ctx.globalAlpha = 1
        ctx.fillStyle = '#000'
        ctx.font = '14px Arial'
        ctx.fillText(roi.label, x1 + 5, y1 - 5)
      })

      requestAnimationFrame(drawOverlay)
    }

    drawOverlay()
  }, [showOverlay])

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
            <div className='webcam-container' style={{position: 'relative'}}>
              <Webcam
                ref={webRef}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: 'user' }}
              />
              <canvas
                ref={canvasRef}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none',
                  display: showOverlay ? 'block' : 'none'
                }}
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

              <button 
                onClick={() => setShowOverlay(!showOverlay)}
                style={{
                  marginTop: '0.5rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: showOverlay ? '#28a745' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer'
                }}
              >
                {showOverlay ? '✓ Guide ON' : 'Show Alignment Guide'}
              </button>
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
                
                <h3 style={{marginTop: '20px'}}>MICR Line Information:</h3>
                <div className="data-item">
                  <strong>Routing Number:</strong> {structuredData.routing_number || 'Not found'}
                </div>
                <div className="data-item">
                  <strong>Account Number:</strong> {structuredData.account_number || 'Not found'}
                </div>
                <div className="data-item">
                  <strong>Check Number:</strong> {structuredData.check_number || 'Not found'}
                </div>
              </div>
            )}
            
            <div className="text-output">
              <h3>Raw OCR Text:</h3>
              <pre>{ocrText}</pre>
            </div>
            
            <div style={{display: 'flex', gap: '10px', marginTop: '10px'}}>
              <button onClick={runOCR} style={{flex: 1}}>{loading ? 'Processing…' : 'Extract Text'}</button>
              <button onClick={visualizeROIs} style={{flex: 1, backgroundColor: '#6c757d'}}>
                {loading ? 'Processing…' : '🔍 Debug ROIs'}
              </button>
            </div>
            
            {showDebug && roiVisualization && (
              <div style={{
                marginTop: '20px', 
                border: '2px solid #007bff', 
                padding: '10px', 
                borderRadius: '5px',
                maxHeight: '600px',
                overflowY: 'auto',
                backgroundColor: '#f8f9fa'
              }}>
                <h3 style={{marginTop: 0}}>ROI Visualization (where the system is looking):</h3>
                <p style={{fontSize: '12px', color: '#666', marginBottom: '10px'}}>
                  Each colored box shows where the system extracts each field:
                  <br />• Green = Date • Blue = Payee • Red = Amount
                  <br />• Cyan = Amount Words • Magenta = Memo
                  <br />• Yellow = Routing • Orange = Account • Purple = Check#
                </p>
                <div style={{overflowX: 'auto'}}>
                  <img src={roiVisualization} style={{maxWidth: '100%', border: '1px solid #ddd', display: 'block'}} alt="ROI visualization" />
                </div>
                <button onClick={() => setShowDebug(false)} style={{marginTop: '10px', backgroundColor: '#dc3545', width: '100%'}}>
                  Close Debug View
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default App
