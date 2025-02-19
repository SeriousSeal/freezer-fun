// src/App.js
import React, { useState } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const parseResponse = (rawData) => {
    // Remove the <think> block (and its internal newlines/whitespaces)
    const withoutThink = rawData.replace(/<think>[\s\S]*?<\/think>/g, '');
  
    // Locate the JSON block by finding the first '{' and the last '}'
    const jsonStart = withoutThink.indexOf('{');
    const jsonEnd = withoutThink.lastIndexOf('}');
    
    if (jsonStart === -1 || jsonEnd === -1) {
      throw new Error('No valid JSON found in response');
    }
    
    // Extract the JSON substring.
    // This preserves any newlines or spaces that are part of the "sentence" value.
    const jsonString = withoutThink.substring(jsonStart, jsonEnd + 1);
    
    try {
      const parsed = JSON.parse(jsonString);
      
      // Validate expected structure
      if (parsed && typeof parsed === 'object' && parsed.sentence && Array.isArray(parsed.used_words)) {
        // Clean up the used_words: remove newlines and extra spaces
        parsed.used_words = parsed.used_words.map(word => word.replace(/\n/g, '').trim());
        
        // The "sentence" field is left untouched so that its newlines/whitespace remain.
        return parsed;
      } else {
        throw new Error('Parsed JSON does not contain the expected keys');
      }
    } catch (err) {
      throw new Error('Failed to parse JSON: ' + err.message);
    }
  };
  

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
  
      const rawData = await response.text();
      console.log('Raw response:', rawData);
      
      const data = parseResponse(rawData);
      setResult(data);
      setError(null);
      
    } catch (err) {
      console.error('Error:', err);
      setError(err.message || 'An unexpected error occurred');
      setResult(null);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Image to Sentence Generator</h1>
      <form onSubmit={handleSubmit}>
        <input type="file" accept="image/*" onChange={handleFileChange} />
        <button type="submit">Upload and Generate</button>
      </form>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {result && (
        <div>
          <h2>Generated Sentence</h2>
          <p><strong>Sentence:</strong> {result.sentence}</p>
          <p><strong>Used Words:</strong> {result.used_words?.join(', ') || 'No words found'}</p>
        </div>
      )}
    </div>
  );
}

export default App;
