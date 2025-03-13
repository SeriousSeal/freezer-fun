import React, { useRef, useEffect, useState, useMemo } from 'react';

// Helper function to normalize text for comparison
const normalizeText = (text) => {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
    .replace(/[^a-z0-9]/g, ''); // Remove special characters
};

// Helper function to get match quality score (lower is better)
const getMatchScore = (word1, word2) => {
  // 0: Exact match
  if (word1 === word2) return 0;
  
  // 1: Case-insensitive exact match
  if (word1.toLowerCase() === word2.toLowerCase()) return 1;
  
  // 2: Umlaut match
  const umlautMap = {
    'ä': 'a', 'ö': 'o', 'ü': 'u',
    'ß': 'ss', 'ae': 'ä', 'oe': 'ö', 'ue': 'ü'
  };
  
  let word1Alt = word1.toLowerCase();
  let word2Alt = word2.toLowerCase();
  
  // Replace umlauts in both words
  Object.entries(umlautMap).forEach(([umlaut, replacement]) => {
    word1Alt = word1Alt.replace(new RegExp(umlaut, 'g'), replacement);
    word2Alt = word2Alt.replace(new RegExp(umlaut, 'g'), replacement);
  });
  
  // Check if words match after umlaut replacement
  if (word1Alt === word2Alt) return 2;
  
  // 3: Very similar words (Levenshtein distance of 1)
  const normalized1 = normalizeText(word1);
  const normalized2 = normalizeText(word2);
  
  if (Math.abs(normalized1.length - normalized2.length) <= 1) {
    const distance = levenshteinDistance(normalized1, normalized2);
    if (distance <= 1) return 3;
  }
  
  // 4: No match
  return 4;
};

// Helper function to check if words are similar
const areWordsSimilar = (word1, word2) => {
  return getMatchScore(word1, word2) < 4;
};

// Levenshtein distance calculation
const levenshteinDistance = (str1, str2) => {
  const m = str1.length;
  const n = str2.length;
  const dp = Array(m + 1).fill().map(() => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (str1[i - 1] === str2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = Math.min(
          dp[i - 1][j - 1] + 1, // substitution
          dp[i - 1][j] + 1,     // deletion
          dp[i][j - 1] + 1      // insertion
        );
      }
    }
  }

  return dp[m][n];
};

// Helper function to check if a word can be constructed from multiple OCR words
const canConstructWord = (targetWord, ocrWords) => {
  const normalizedTarget = normalizeText(targetWord);
  let remainingChars = normalizedTarget;
  
  // Try to match OCR words against the target word
  for (const ocrWord of ocrWords) {
    const normalizedOcr = normalizeText(ocrWord);
    if (remainingChars.includes(normalizedOcr)) {
      remainingChars = remainingChars.replace(normalizedOcr, '');
    }
  }
  
  return remainingChars === '';
};

// Helper function to find all parts that make up a word
const findWordParts = (targetWord, ocrWords) => {
  const normalizedTarget = normalizeText(targetWord);
  let remainingChars = normalizedTarget;
  const parts = [];
  
  // Try to match OCR words against the target word
  for (const ocrWord of ocrWords) {
    const normalizedOcr = normalizeText(ocrWord);
    if (remainingChars.includes(normalizedOcr)) {
      parts.push(ocrWord);
      remainingChars = remainingChars.replace(normalizedOcr, '');
    }
  }
  
  return parts;
};

const ImageWithWords = React.memo(({ imageData, ocrData, usedWords, zoom = 1, offset = { x: 0, y: 0 }, isDragging = false, highlightedWord = null }) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(null);
  const imageRef = useRef(null);
  const canvasRef = useRef(null);

  // Debug logging for props
  useEffect(() => {
    console.log('ImageWithWords props:', {
      hasImageData: !!imageData,
      hasOcrData: !!ocrData,
      magnets: ocrData?.magnets?.length,
      usedWords,
      highlightedWord
    });
  }, [imageData, ocrData, usedWords, highlightedWord]);

  // Memoize the transform style to prevent unnecessary recalculations
  const transformStyle = useMemo(() => ({
    transform: `scale(${zoom}) translate(${offset.x / zoom}px, ${offset.y / zoom}px)`,
    transformOrigin: 'center center',
    transition: isDragging ? 'none' : 'transform 0.1s ease-out',
    willChange: 'transform',
    backfaceVisibility: 'hidden',
    WebkitBackfaceVisibility: 'hidden',
    WebkitTransform: `scale(${zoom}) translate(${offset.x / zoom}px, ${offset.y / zoom}px)`,
    WebkitTransformOrigin: 'center center'
  }), [zoom, offset.x, offset.y, isDragging]);

  // Memoize the image style to prevent unnecessary recalculations
  const imageStyle = useMemo(() => ({
    maxWidth: '100%',
    maxHeight: '100%',
    width: 'auto',
    height: 'auto',
    objectFit: 'contain',
    userSelect: 'none',
    pointerEvents: 'none',
    ...transformStyle
  }), [transformStyle]);

  useEffect(() => {
    if (!imageData) {
      console.log("Missing image data");
      return;
    }

    // Create Image object from pre-encoded data URL
    const img = new Image();
    
    img.onload = () => {
      console.log("Image loaded successfully");
      setImageLoaded(true);
      setImageError(null);
    };
    
    img.onerror = (error) => {
      console.error("Error loading image:", error);
      setImageLoaded(false);
      setImageError("Failed to load image");
    };
    
    try {
      // Use the pre-encoded data URL directly
      img.src = imageData;
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
  }, [imageData]);

  // Draw word boxes on canvas
  useEffect(() => {
    if (!imageLoaded || !ocrData?.magnets || !canvasRef.current) {
      console.log('Skipping canvas drawing:', {
        imageLoaded,
        hasOcrData: !!ocrData,
        hasCanvas: !!canvasRef.current
      });
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;

    // Get the actual displayed dimensions of the image
    const displayWidth = img.clientWidth;
    const displayHeight = img.clientHeight;

    // Calculate the scale factors
    const scaleX = displayWidth / img.naturalWidth;
    const scaleY = displayHeight / img.naturalHeight;

    console.log('Drawing canvas with dimensions:', {
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      displayWidth,
      displayHeight,
      scaleX,
      scaleY,
      magnetsCount: ocrData.magnets.length,
      usedWordsCount: usedWords.length
    });

    // Debug: Log all available words from OCR
    console.log('Available words from OCR:', ocrData.magnets.map(m => ({
      text: m.text,
      confidence: m.confidence
    })));

    // Debug: Log all used words
    console.log('Used words to mark:', usedWords);

    // Set canvas size to match the natural image size
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Create a map to track which OCR words have been matched
    const matchedOcrWords = new Set();

    // First pass: Find exact matches and constructed words
    usedWords.forEach(word => {
      let bestMatch = null;
      let bestScore = 4;
      let bestMagnet = null;
      let wordParts = [];

      // First try exact matches
      ocrData.magnets.forEach(magnet => {
        if (!matchedOcrWords.has(magnet.text)) {
          const score = getMatchScore(word, magnet.text);
          if (score < bestScore) {
            bestScore = score;
            bestMatch = word;
            bestMagnet = magnet;
          }
        }
      });

      // If no exact match found, try to construct the word
      if (bestScore === 4) {
        const availableWords = ocrData.magnets
          .filter(m => !matchedOcrWords.has(m.text))
          .map(m => m.text);
        
        if (canConstructWord(word, availableWords)) {
          wordParts = findWordParts(word, availableWords);
          bestScore = 3; // Use a good score for constructed words
        }
      }

      // If we found a match or can construct the word, mark it/them
      if (bestScore < 4) {
        if (bestMagnet) {
          // Handle exact match
          matchedOcrWords.add(bestMagnet.text);
          console.log(`Word matched: "${word}" with "${bestMagnet.text}" (score: ${bestScore})`);
          
          const position = bestMagnet.position;
          const points = position.points;

          // Draw box
          ctx.beginPath();
          ctx.moveTo(points[0][0], points[0][1]);
          for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0], points[i][1]);
          }
          ctx.closePath();

          // Set style based on whether this word is highlighted
          if (highlightedWord && areWordsSimilar(highlightedWord, bestMagnet.text)) {
            ctx.fillStyle = 'rgba(255, 255, 0, 0.3)';
            ctx.strokeStyle = '#FFD700';
            ctx.lineWidth = 2;
          } else {
            ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
            ctx.strokeStyle = '#00FF00';
            ctx.lineWidth = 1;
          }

          ctx.fill();
          ctx.stroke();
        } else if (wordParts.length > 0) {
          // Handle constructed word
          console.log(`Word constructed: "${word}" from parts:`, wordParts);
          
          // Find and mark all parts
          wordParts.forEach(part => {
            const magnet = ocrData.magnets.find(m => 
              normalizeText(m.text) === normalizeText(part) && 
              !matchedOcrWords.has(m.text)
            );
            
            if (magnet) {
              matchedOcrWords.add(magnet.text);
              const position = magnet.position;
              const points = position.points;

              // Draw box
              ctx.beginPath();
              ctx.moveTo(points[0][0], points[0][1]);
              for (let i = 1; i < points.length; i++) {
                ctx.lineTo(points[i][0], points[i][1]);
              }
              ctx.closePath();

              // Set style based on whether this word is highlighted
              if (highlightedWord && areWordsSimilar(highlightedWord, word)) {
                ctx.fillStyle = 'rgba(255, 255, 0, 0.3)';
                ctx.strokeStyle = '#FFD700';
                ctx.lineWidth = 2;
              } else {
                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                ctx.strokeStyle = '#00FF00';
                ctx.lineWidth = 1;
              }

              ctx.fill();
              ctx.stroke();
            }
          });
        }
      }
    });

    // Debug: Check for any used words that weren't found in OCR data
    const unmatchedWords = usedWords.filter(word => 
      !ocrData.magnets.some(m => areWordsSimilar(word, m.text))
    );
    if (unmatchedWords.length > 0) {
      console.warn('Words not found in OCR data:', unmatchedWords);
    }
  }, [imageLoaded, ocrData, usedWords, highlightedWord]);

  return (
    <div style={{ 
      width: '100%', 
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {!imageLoaded && !imageError && (
        <div style={{ textAlign: 'center', border: '1px solid #ccc' }}>
          Loading image...
        </div>
      )}
      
      {imageError && (
        <div style={{ textAlign: 'center', border: '1px solid #ccc', color: 'red' }}>
          {imageError}
        </div>
      )}
      
      {imageLoaded && imageData && (
        <div style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <img 
            ref={imageRef}
            src={imageData}
            alt="Processed" 
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              width: 'auto',
              height: 'auto',
              objectFit: 'contain',
              userSelect: 'none',
              pointerEvents: 'none',
              ...transformStyle
            }}
            onLoad={() => {
              console.log('Image loaded with dimensions:', {
                naturalWidth: imageRef.current.naturalWidth,
                naturalHeight: imageRef.current.naturalHeight,
                clientWidth: imageRef.current.clientWidth,
                clientHeight: imageRef.current.clientHeight
              });
            }}
          />
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: `translate(-50%, -50%) ${transformStyle.transform}`,
              transformOrigin: 'center center',
              pointerEvents: 'none',
              maxWidth: '100%',
              maxHeight: '100%',
              width: 'auto',
              height: 'auto'
            }}
          />
        </div>
      )}
    </div>
  );
});

export default function ImageWithWordsComponent(props) {
  return <ImageWithWords {...props} />;
}
