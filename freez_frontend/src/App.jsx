import React, { useState } from 'react';
import ImageWithWords from './components/ImageWithWords';

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
  
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
        return;
      }
  
      // The response should now be properly formatted JSON directly from the backend
      const data = await response.json();
      console.log('Received data:', data);
      
      if (data.sentence && data.used_words && data.image_base64 && data.ocr_data) {
        setResult(data);
        setError(null);
      } else {
        setError('Received improperly formatted response');
        setResult(null);
      }
      
    } catch (err) {
      console.error('Error:', err);
      setError(err.message || 'An unexpected error occurred');
      setResult(null);
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
        <button type="submit" disabled={!file}>Generate Sentence</button>
      </form>
      
      {error && <p style={{ color: 'red' }}>{error}</p>}
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {/* Image preview before submission */}
        {imagePreview && !result && (
          <div style={{ flex: '1', minWidth: '300px' }}>
            <h2>Selected Image</h2>
            <img 
              src={imagePreview} 
              alt="Selected" 
              style={{ maxWidth: '100%', border: '1px solid #ccc' }} 
            />
          </div>
        )}
        
        {/* Result section */}
        {result && (
          <>
            <div style={{ flex: '1', minWidth: '300px' }}>
              <h2>Detected Words</h2>
              <ImageWithWords 
                imageData={result.image_base64} 
                ocrData={result.ocr_data} 
              />
            </div>
            <div style={{ flex: '1', minWidth: '300px' }}>
              <h2>Generated Sentence</h2>
              <p style={{ fontSize: '18px', fontWeight: 'bold' }}>{result.sentence}</p>
              <h3>Used Words</h3>
              <ul>
                {result.used_words.map((word, index) => (
                  <li key={index}>{word}</li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
