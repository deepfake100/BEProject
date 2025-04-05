import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Detect.css';

function Detect() {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [uploadButtonText, setUploadButtonText] = useState('Upload Files');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);
  const resultRef = useRef(null);

  // Define the server URL as a constant
  const SERVER_URL = 'http://127.0.0.1:5000';

  // Scroll to results when they appear
  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'center'
      });
    }
  }, [result]);

  const handleButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleFileUpload = async (event) => {
    const selectedFile = event.target.files[0];
    if (!selectedFile) return;

    // Reset error state and result
    setError('');
    setResult(null);
    setVideoUrl('');

    // Check if file is a video
    if (!selectedFile.type.startsWith('video/')) {
      setError('Please upload a video file');
      alert('Please upload a video file');
      return;
    }

    // Check file size (e.g., 100MB limit)
    const maxSize = 100 * 1024 * 1024; // 100MB in bytes
    if (selectedFile.size > maxSize) {
      setError('File size too large. Maximum size is 100MB');
      alert('File size too large. Maximum size is 100MB');
      return;
    }

    // Create URL for video preview
    const videoPreviewUrl = URL.createObjectURL(selectedFile);
    setVideoUrl(videoPreviewUrl);

    console.log('Selected file:', selectedFile.name, 'Type:', selectedFile.type, 'Size:', selectedFile.size);

    setFile(selectedFile);
    setFileName(selectedFile.name);
    setIsUploading(true);
    setUploadButtonText('Uploading...');

    const formData = new FormData();
    formData.append('video', selectedFile);

    try {
      console.log('Sending upload request to server...');
      const response = await axios.post(`${SERVER_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000, // 30 second timeout
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log(`Upload progress: ${percentCompleted}%`);
        }
      });

      console.log('Server response:', response.data);

      if (response.status === 200 && response.data.message === 'File uploaded successfully') {
        setUploadButtonText('Change');
        setError('');
        console.log('File uploaded successfully:', response.data);
      } else {
        throw new Error('Upload response was not successful');
      }
    } catch (error) {
      console.error('Upload error:', error);
      let errorMessage = 'Failed to upload file';
      
      if (error.code === 'ERR_NETWORK') {
        errorMessage = 'Network error: Please check if the backend server is running at http://127.0.0.1:5000';
      } else if (error.code === 'ECONNREFUSED') {
        errorMessage = 'Cannot connect to server. Please make sure the backend server is running.';
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = 'Upload timed out. Please try again.';
      } else if (error.response) {
        errorMessage = error.response.data.error || error.message;
      }
      
      setError(errorMessage);
      alert(errorMessage);
      setUploadButtonText('Upload Failed');
      // Clean up video URL on error
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
        setVideoUrl('');
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Clean up video URL when component unmounts
  React.useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  const handleDetect = async () => {
    if (!fileName) return;

    setIsDetecting(true);
    setError('');
    setResult(null);

    try {
      console.log('Starting detection...');
      const response = await axios.get(`${SERVER_URL}/detect`, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        timeout: 60000, // 60 second timeout for detection
        withCredentials: true
      });
      
      console.log('Detection response:', response.data);
      
      if (response.status === 200) {
        setResult(response.data);
        console.log('Detection result:', response.data);
      } else {
        throw new Error('Detection response was not successful');
      }
    } catch (error) {
      console.error('Detection error:', error);
      let errorMessage = 'Detection failed';
      
      if (error.code === 'ERR_NETWORK') {
        errorMessage = 'Network error: Please check if the backend server is running at http://127.0.0.1:5000';
      } else if (error.code === 'ECONNREFUSED') {
        errorMessage = 'Cannot connect to server. Please make sure the backend server is running.';
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = 'Detection timed out. Please try again.';
      } else if (error.response) {
        errorMessage = error.response.data.error || error.message;
        console.error('Server error details:', error.response.data);
      }
      
      setError(errorMessage);
      alert(errorMessage);
    } finally {
      setIsDetecting(false);
    }
  };

  return (
    <div className="detect-page">
      <div className="detect-banner">
        <div className="detect-heading">
          <h1>Click here to detect <br />deepfake</h1>
        </div>
        <div className="detect-upload-button">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            disabled={isUploading}
          />
          <button 
            onClick={handleButtonClick}
            disabled={isUploading}
            style={{ cursor: isUploading ? 'not-allowed' : 'pointer' }}
          >
            {uploadButtonText}
          </button>
        </div>
      </div>

      {/* Only show file details when there's a file or error */}
      {(fileName || error) && (
        <div className="detect-file-details">
          {videoUrl && (
            <div className="video-preview">
              <video 
                src={videoUrl} 
                controls 
                className="preview-video"
              />
            </div>
          )}
          {fileName && <p>Uploaded file: {fileName}</p>}
          {error && <p style={{ color: 'red' }}>{error}</p>}
          {fileName && !error && (
            <button 
              className="detect-button"
              onClick={handleDetect}
              disabled={isDetecting}
            >
              {isDetecting ? 'Detecting...' : 'Detect'}
            </button>
          )}
        </div>
      )}

      {/* Only show result when there's a result */}
      {result && (
        <div className="detect-result" ref={resultRef}>
          <h1>Result: <span className={result.is_real ? "detect-real" : "detect-fake"}>
            {result.is_real ? "Real" : "Fake"}
          </span></h1>
          <h1>Confidence: <span className="detect-confidance">{result.confidence.toFixed(2)}%</span></h1>
        </div>
      )}
    </div>
  );
}

export default Detect;
