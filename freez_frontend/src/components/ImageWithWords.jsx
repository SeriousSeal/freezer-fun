import React, { useRef, useEffect, useState } from 'react';

const ImageWithWords = ({ imageData, ocrData, usedWords = [] }) => {
  const canvasRef = useRef(null);
  // Add state to track if image loaded successfully
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(null);

  useEffect(() => {
    if (!imageData || !ocrData || !ocrData.magnets) {
      console.log("Missing data for rendering image with words");
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Clear any previous content
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Show loading state
    ctx.font = '16px Arial';
    ctx.fillStyle = 'gray';
    ctx.fillText('Loading image...', 10, 30);
    
    // Create Image object from base64 data
    const img = new Image();
    
    img.onload = () => {
      console.log("Image loaded successfully, dimensions:", img.width, "x", img.height);
      setImageLoaded(true);
      setImageError(null);
      
      // Set canvas dimensions to match image
      canvas.width = img.width;
      canvas.height = img.height;
      
      // Draw image
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      
      // Process each detected word
      if (ocrData && ocrData.magnets) {
        ocrData.magnets.forEach((magnet, index) => {
          if (!magnet || !magnet.text) return;
          
          const text = magnet.text;
          
          // Check if this word is used in the generated sentence
          const isUsed = usedWords.some(word => 
            word.toLowerCase() === text.toLowerCase()
          );
          
          // Draw the annotation
          if (magnet.box && 
              typeof magnet.box.x === 'number' && 
              typeof magnet.box.y === 'number' && 
              typeof magnet.box.w === 'number' && 
              typeof magnet.box.h === 'number') {
            
            const { box } = magnet;
            
            // Set style based on whether the word is used
            ctx.lineWidth = isUsed ? 3 : 1;
            ctx.strokeStyle = isUsed ? 'green' : 'red';
            ctx.fillStyle = isUsed ? 'green' : 'red';
            ctx.font = isUsed ? 'bold 16px Arial' : '16px Arial';
            
            // Draw rectangle
            ctx.strokeRect(box.x, box.y, box.w, box.h);
            
            // Draw text above the box
            ctx.fillText(text, box.x, box.y - 5);
            
            // If word is used, add a highlight effect
            if (isUsed) {
              ctx.globalAlpha = 0.2;
              ctx.fillStyle = 'yellow';
              ctx.fillRect(box.x, box.y, box.w, box.h);
              ctx.globalAlpha = 1.0;
              ctx.fillStyle = 'green';
            }
          }
        });
      }
    };
    
    img.onerror = (error) => {
      console.error("Error loading image:", error);
      setImageLoaded(false);
      setImageError("Failed to load image");
      
      // Show error message on canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 400;
      canvas.height = 100;
      ctx.font = '16px Arial';
      ctx.fillStyle = 'red';
      ctx.fillText('Error loading image', 10, 30);
    };
    
    try {
      // Set image source with proper formatting
      if (imageData.startsWith('data:image')) {
        img.src = imageData;
      } else {
        img.src = `data:image/jpeg;base64,${imageData}`;
      }
      console.log("Image source set");
    } catch (error) {
      console.error("Error setting image source:", error);
      setImageError("Invalid image data");
    }
    
    // Clean-up function
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [imageData, ocrData, usedWords]);

  // Fallback to original image if canvas rendering fails
  return (
    <div className="image-container">
      <canvas 
        ref={canvasRef} 
        style={{ 
          maxWidth: '100%', 
          border: '1px solid #ccc', 
          display: imageLoaded ? 'block' : 'none'
        }} 
      />
      
      {!imageLoaded && !imageError && (
        <div style={{ padding: '20px', textAlign: 'center', border: '1px solid #ccc' }}>
          Loading image...
        </div>
      )}
      
      {imageError && (
        <div style={{ padding: '20px', textAlign: 'center', border: '1px solid #ccc', color: 'red' }}>
          {imageError}
        </div>
      )}
      
      {/* Fallback image display if canvas doesn't work */}
      {!imageLoaded && !imageError && imageData && (
        <div style={{ marginTop: '10px' }}>
          <p>Fallback image:</p>
          <img 
            src={imageData.startsWith('data:image') ? imageData : `data:image/jpeg;base64,${imageData}`}
            alt="Processed" 
            style={{ maxWidth: '100%', border: '1px solid #ccc' }} 
          />
        </div>
      )}
      
      <div className="legend" style={{ marginTop: '10px', fontSize: '14px' }}>
        <div><span style={{ color: 'green', fontWeight: 'bold' }}>■</span> Used in sentence</div>
        <div><span style={{ color: 'red' }}>■</span> Detected but not used</div>
      </div>
    </div>
  );
};

export default function ImageWithWordsComponent(props) {
  return <ImageWithWords {...props} />;
}
