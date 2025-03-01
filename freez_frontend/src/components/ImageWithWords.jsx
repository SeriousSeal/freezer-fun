import React, { useRef, useEffect } from 'react';

const ImageWithWords = ({ imageData, ocrData }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!imageData || !ocrData || !ocrData.magnets) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Create Image object from base64 data
    const img = new Image();
    img.src = `data:image/jpeg;base64,${imageData}`;
    
    img.onload = () => {
      // Set canvas dimensions to match image
      canvas.width = img.width;
      canvas.height = img.height;
      
      // Draw image
      ctx.drawImage(img, 0, 0);
      
      // Draw boxes around detected words
      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.font = '16px Arial';
      ctx.fillStyle = 'red';

      ocrData.magnets.forEach((magnet) => {
        const { box, text } = magnet;
        
        // Draw rectangle
        ctx.strokeRect(box.x, box.y, box.w, box.h);
        
        // Draw text above the box
        ctx.fillText(text, box.x, box.y - 5);
      });
    };
  }, [imageData, ocrData]);

  return (
    <div className="image-container">
      <canvas ref={canvasRef} style={{ maxWidth: '100%', border: '1px solid #ccc' }} />
    </div>
  );
};

export default ImageWithWords;
