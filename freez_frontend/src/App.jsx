import React, { useState, useRef, useEffect } from 'react';
import ImageWithWords from './components/ImageWithWords';
import detectZoom from './components/detect-zoom';

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [lastOffset, setLastOffset] = useState({ x: 0, y: 0 });
  const [highlightedWord, setHighlightedWord] = useState(null);
  const [instructions, setInstructions] = useState('');
  const previewContainerRef = useRef(null);
  const resultContainerRef = useRef(null);

  // Add effect to prevent browser zoom
  useEffect(() => {
    const preventZoom = (e) => {
      if (e.ctrlKey) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
    };

    const preventZoomKeys = (e) => {
      if (e.ctrlKey && (e.key === '+' || e.key === '-' || e.key === '=')) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
    };

    // Add event listeners to both containers
    const containers = [previewContainerRef.current, resultContainerRef.current].filter(Boolean);
    containers.forEach(container => {
      container.addEventListener('DOMMouseScroll', preventZoom, { passive: false });
      container.addEventListener('MozMousePixelScroll', preventZoom, { passive: false });
      container.addEventListener('wheel', preventZoom, { passive: false });
      container.addEventListener('keydown', preventZoomKeys, { passive: false });
    });

    // Add global event listeners
    window.addEventListener('DOMMouseScroll', preventZoom, { passive: false });
    window.addEventListener('MozMousePixelScroll', preventZoom, { passive: false });
    window.addEventListener('wheel', preventZoom, { passive: false });
    window.addEventListener('keydown', preventZoomKeys, { passive: false });

    // Monitor browser zoom level
    const checkZoom = () => {
      const zoomInfo = detectZoom();
      if (zoomInfo.zoom !== 1) {
      }
    };

    checkZoom();
    window.addEventListener('resize', checkZoom);

    return () => {
      containers.forEach(container => {
        container.removeEventListener('DOMMouseScroll', preventZoom);
        container.removeEventListener('MozMousePixelScroll', preventZoom);
        container.removeEventListener('wheel', preventZoom);
        container.removeEventListener('keydown', preventZoomKeys);
      });
      window.removeEventListener('DOMMouseScroll', preventZoom);
      window.removeEventListener('MozMousePixelScroll', preventZoom);
      window.removeEventListener('wheel', preventZoom);
      window.removeEventListener('keydown', preventZoomKeys);
      window.removeEventListener('resize', checkZoom);
    };
  }, []);

  const parseResponse = (rawData) => {
    try {
      // Remove the <think> block and any leading/trailing whitespace
      const withoutThink = rawData.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
      
      // Try direct JSON parsing first (in case it's already valid JSON)
      try {
        const directParse = JSON.parse(withoutThink);
        if (directParse && typeof directParse === 'object' && directParse.sentence) {
          return directParse;
        }
      } catch (e) {
        // Continue with more robust parsing if direct parse fails
      }
      
      // Find JSON-like content using regex
      const jsonRegex = /\{[\s\S]*\}/;
      const jsonMatch = withoutThink.match(jsonRegex);
      
      if (!jsonMatch) {
        throw new Error('No valid JSON structure found in response');
      }
      
      const jsonString = jsonMatch[0];
      
      // Parse the extracted JSON
      const parsed = JSON.parse(jsonString);
      
      // Validate expected structure
      if (parsed && typeof parsed === 'object') {
        // Make sure we have the required fields, with fallbacks if missing
        const result = {
          sentence: parsed.sentence || '',
          used_words: Array.isArray(parsed.used_words) 
            ? parsed.used_words.map(word => word.replace(/\n/g, '').trim()) 
            : []
        };
        
        return result;
      } else {
        throw new Error('Parsed JSON does not contain the expected structure');
      }
    } catch (err) {
      throw new Error('Failed to parse response: ' + err.message);
    }
  };

  // Add a debugging function to log the results
  const logResults = (data) => {
    // Verify each used word exists in the OCR data
    if (data.used_words && data.ocr_data && data.ocr_data.magnets) {
      data.used_words.forEach(word => {
        const found = data.ocr_data.magnets.some(m => 
          m.text && m.text.toLowerCase() === word.toLowerCase()
        );
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || loading) return;
  
    // Clear previous results
    setResult(null);
    setError(null);
    setLoading(true);
    setProcessingStep('Preparing image...');
    
    const formData = new FormData();
    formData.append('file', file);
    if (instructions.trim()) {
      formData.append('instructions', instructions.trim());
    }
  
    try {
      setProcessingStep('Processing image...');
      const response = await fetch('http://localhost:8000/generate-sentence-from-image/', {
        method: 'POST',
        body: formData,
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Server error occurred');
      }
  
      setProcessingStep('Analyzing results...');
      const data = await response.json();
      
      if (data.sentence && data.used_words && data.base64_image && data.ocr_data) {
        // Encode the image once when we receive it
        const encodedImage = data.base64_image.startsWith('data:image') 
          ? data.base64_image 
          : `data:image/jpeg;base64,${data.base64_image}`;
        
        setResult({
          sentence: data.sentence,
          used_words: data.used_words,
          image_base64: encodedImage,
          ocr_data: data.ocr_data
        });
        setError(null);
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (err) {
      console.error('Error:', err);
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
      setProcessingStep('');
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setResult(null);
    setError(null);
    
    // Create image preview
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setImagePreview(null);
    }
  };

  const handleWheel = (e, containerRef) => {
    if (e.ctrlKey) {
      e.preventDefault();
      e.stopPropagation();
      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const isOverContainer = (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      );

      if (!isOverContainer) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomInfo = detectZoom();
      const browserZoom = zoomInfo.zoom;

      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const newZoom = Math.max(0.5, Math.min(3, zoom + delta));

      const scale = newZoom / zoom;
      const newOffsetX = mouseX - (mouseX - offset.x) * scale;
      const newOffsetY = mouseY - (mouseY - offset.y) * scale;

      setZoom(newZoom);
      setOffset({ x: newOffsetX, y: newOffsetY });
    }
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({
      x: e.clientX - offset.x,
      y: e.clientY - offset.y
    });
    setLastOffset(offset);
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      const newOffset = {
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      };
      setOffset(newOffset);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div style={{ 
      display: 'flex',
      minHeight: '100vh',
      width: '100%',
      margin: 0,
      padding: 0,
      boxSizing: 'border-box'
    }}>
      {/* Left side - Controls */}
      <div style={{ 
        width: '400px',
        minWidth: '400px',
        backgroundColor: '#ffffff',
        borderRight: '1px solid #dee2e6',
        overflow: 'auto',
        padding: '20px',
        boxSizing: 'border-box'
      }}>
        <h1 style={{ 
          marginBottom: '30px',
          fontSize: '24px',
          color: '#333'
        }}>Poetry Magnets App</h1>
        
        <form onSubmit={handleSubmit} style={{ 
          display: 'flex',
          flexDirection: 'column',
          gap: '15px',
          marginBottom: '30px'
        }}>
          <div style={{ 
            border: '2px dashed #ccc',
            padding: '20px',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <input 
              type="file" 
              onChange={handleFileChange} 
              accept="image/*"
              style={{ display: 'none' }}
              id="file-input"
            />
            <label 
              htmlFor="file-input"
              style={{ 
                cursor: 'pointer',
                display: 'block',
                padding: '10px',
                backgroundColor: '#fff',
                borderRadius: '4px',
                color: '#333'
              }}
            >
              {file ? file.name : 'Choose an image file'}
            </label>
          </div>

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '5px'
          }}>
            <label 
              htmlFor="instructions"
              style={{
                fontSize: '14px',
                color: '#333',
                fontWeight: '500'
              }}
            >
              Instructions (optional)
            </label>
            <input
              type="text"
              id="instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Enter instructions for sentence generation..."
              style={{
                padding: '10px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                fontSize: '14px',
                color: '#333',
                backgroundColor: '#fff'
              }}
            />
          </div>
          
          <button 
            type="submit" 
            disabled={!file || loading}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              backgroundColor: loading ? '#ccc' : '#007bff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.3s'
            }}
          >
            {loading ? 'Processing...' : 'Generate Sentence'}
          </button>
        </form>
        
        {error && (
          <div style={{ 
            color: '#dc3545',
            padding: '10px',
            backgroundColor: '#fff3f3',
            borderRadius: '4px',
            marginTop: '20px'
          }}>
            {error}
          </div>
        )}
        
        {loading && (
          <div style={{ 
            color: '#0056b3',
            padding: '10px',
            backgroundColor: '#f0f8ff',
            borderRadius: '4px',
            marginTop: '20px',
            textAlign: 'center'
          }}>
            {processingStep}
          </div>
        )}

        {/* Results moved to left side */}
        {result && !loading && (
          <div style={{ marginTop: '30px' }}>
            <h2 style={{ color: '#333', marginBottom: '15px' }}>Generated Sentence</h2>
            <div style={{ 
              padding: '15px',
              backgroundColor: '#fff',
              borderRadius: '4px',
              marginBottom: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <p style={{ 
                fontSize: '18px', 
                fontWeight: 'bold',
                color: '#333',
                margin: 0
              }}>{result.sentence}</p>
            </div>
            <h3 style={{ color: '#333', marginBottom: '10px' }}>Used Words ({result.used_words.length})</h3>
            <ul style={{ 
              listStyle: 'none',
              padding: 0,
              display: 'flex',
              flexWrap: 'wrap',
              gap: '10px'
            }}>
              {result.used_words.map((word, index) => (
                <li 
                  key={index}
                  onClick={() => {
                    setHighlightedWord(word === highlightedWord ? null : word);
                  }}
                  style={{
                    backgroundColor: word === highlightedWord ? '#ffd700' : '#e9ecef',
                    padding: '5px 10px',
                    borderRadius: '15px',
                    fontSize: '14px',
                    color: '#495057',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    border: word === highlightedWord ? '2px solid #ffd700' : '2px solid transparent',
                    boxShadow: word === highlightedWord ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                    transform: word === highlightedWord ? 'scale(1.05)' : 'scale(1)',
                    ':hover': {
                      backgroundColor: word === highlightedWord ? '#ffd700' : '#dee2e6',
                      transform: 'scale(1.05)',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.05)';
                    e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                  }}
                  onMouseLeave={(e) => {
                    if (word !== highlightedWord) {
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.boxShadow = 'none';
                    }
                  }}
                >
                  {word}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Right side - Results */}
      <div style={{ 
        flex: 1,
        minWidth: 0,
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        padding: '20px',
        boxSizing: 'border-box'
      }}>
        {/* Image preview before submission */}
        {imagePreview && !result && !loading && (
          <div style={{ 
            flex: 1,
            display: 'flex', 
            flexDirection: 'column',
            width: '100%',
            minWidth: 0,
            minHeight: 0
          }}>
            <h2 style={{ color: '#333', margin: '0 0 10px 0' }}>Selected Image</h2>
            <div 
              ref={previewContainerRef}
              onWheel={(e) => handleWheel(e, previewContainerRef)}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ 
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                backgroundColor: '#ffffff',
                borderRadius: '4px',
                position: 'relative',
                width: '100%',
                minHeight: 0,
                cursor: isDragging ? 'grabbing' : 'grab'
              }}
            >
              <img 
                src={imagePreview} 
                alt="Selected" 
                style={{ 
                  maxWidth: '100%',
                  maxHeight: '100%',
                  width: 'auto',
                  height: 'auto',
                  objectFit: 'contain',
                  transform: `scale(${zoom}) translate(${offset.x / zoom}px, ${offset.y / zoom}px)`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                  userSelect: 'none',
                  pointerEvents: 'none'
                }} 
              />
            </div>
          </div>
        )}
        
        {/* Result section - only image */}
        {result && !loading && (
          <div style={{ 
            flex: 1,
            display: 'flex', 
            flexDirection: 'column',
            width: '100%',
            minWidth: 0,
            minHeight: 0
          }}>
            <h2 style={{ color: '#333', margin: '0 0 10px 0' }}>Detected Words</h2>
            <div 
              ref={resultContainerRef}
              onWheel={(e) => handleWheel(e, resultContainerRef)}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ 
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                backgroundColor: '#ffffff',
                borderRadius: '4px',
                position: 'relative',
                width: '100%',
                minHeight: 0,
                cursor: isDragging ? 'grabbing' : 'grab'
              }}
            >
              <div style={{ 
                userSelect: 'none',
                pointerEvents: 'none',
                width: '100%',
                height: '100%'
              }}>
                <ImageWithWords 
                  imageData={result.image_base64} 
                  ocrData={result.ocr_data} 
                  usedWords={result.used_words}
                  zoom={zoom}
                  offset={offset}
                  isDragging={isDragging}
                  highlightedWord={highlightedWord}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
