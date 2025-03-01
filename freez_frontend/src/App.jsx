import React, { useState } from 'react';
import ImageWithWords from './components/ImageWithWords';

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);

  const parseResponse = (rawData) => {
    try {
      console.log('Parsing response:', rawData);
      
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
        console.log('Direct parsing failed, trying to extract JSON');
      }
      
      // Find JSON-like content using regex
      const jsonRegex = /\{[\s\S]*\}/;
      const jsonMatch = withoutThink.match(jsonRegex);
      
      if (!jsonMatch) {
        throw new Error('No valid JSON structure found in response');
      }
      
      const jsonString = jsonMatch[0];
      console.log('Extracted JSON string:', jsonString);
      
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
      console.error('Parse error details:', err);
      throw new Error('Failed to parse response: ' + err.message);
    }
  };

  // Add a debugging function to log the results
  const logResults = (data) => {
    console.log("Complete API response:", data);
    console.log("OCR data structure:", data.ocr_data);
    console.log("Detected words:", data.ocr_data?.magnets?.map(m => m.text));
    console.log("Words used in sentence:", data.used_words);
    
    // Verify each used word exists in the OCR data
    if (data.used_words && data.ocr_data && data.ocr_data.magnets) {
      data.used_words.forEach(word => {
        const found = data.ocr_data.magnets.some(m => 
          m.text && m.text.toLowerCase() === word.toLowerCase()
        );
        console.log(`Word "${word}" ${found ? 'found' : 'NOT FOUND'} in OCR data`);
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
  
    // Clear previous results
    setResult(null);
    setError(null);
    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
  
    try {
      const response = await fetch('http://localhost:8000/generate-sentence-from-image/', {
        method: 'POST',
        body: formData,
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        setError(errorData.error || 'Something went wrong');
        setLoading(false);
        return;
      }
  
      const data = await response.json();
      console.log('Received data:', data);
      
      if (data.sentence && data.used_words && data.image_base64 && data.ocr_data) {
        // Debug the results
        logResults(data);
        
        // Set result and stop loading
        setResult(data);
        setError(null);
      } else {
        setError('Received improperly formatted response');
      }
    } catch (err) {
      console.error('Error:', err);
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    
    // Create image preview
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setImagePreview(null);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1>Poetry Magnets App</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <input type="file" onChange={handleFileChange} accept="image/*" />
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Processing...' : 'Generate Sentence'}
        </button>
      </form>
      
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {loading && <p style={{ color: 'blue' }}>Processing image and generating sentence...</p>}
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {/* Image preview before submission */}
        {imagePreview && !result && !loading && (
          <div style={{ flex: '1', minWidth: '300px' }}>
            <h2>Selected Image</h2>
            <img 
              src={imagePreview} 
              alt="Selected" 
              style={{ maxWidth: '100%', border: '1px solid #ccc' }} 
            />
          </div>
        )}
        
        {/* Result section - only show when result exists and not loading */}
        {result && !loading && (
          <>
            <div style={{ flex: '1', minWidth: '300px' }}>
              <h2>Detected Words</h2>
              {/* Only render one instance of ImageWithWords */}
              <ImageWithWords 
                key={`image-${Date.now()}`}  // Force remount each time
                imageData={result.image_base64} 
                ocrData={result.ocr_data} 
                usedWords={result.used_words}
              />
            </div>
            <div style={{ flex: '1', minWidth: '300px' }}>
              <h2>Generated Sentence</h2>
              <p style={{ fontSize: '18px', fontWeight: 'bold' }}>{result.sentence}</p>
              <h3>Used Words ({result.used_words.length})</h3>
              <ul>
                {result.used_words.map((word, index) => (
                  <li key={index}>{word}</li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
      
      {/* Only show debug info when we have a result */}
      {result && (
        <div style={{ marginTop: '30px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '5px' }}>
          <details>
            <summary>Debug Information</summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

export default App;
