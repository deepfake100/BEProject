from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil
import logging
from service.detect import detect_fake_video

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS with specific options
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173"],  # Only allow the frontend origin
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "X-CSRFToken"],
        "max_age": 600
    }
})

# Configure upload folder
UPLOAD_FOLDER = 'uploaded'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Created upload folder: {UPLOAD_FOLDER}")

# Check if model file exists
MODEL_PATH = './service/df_model.pt'
if not os.path.exists(MODEL_PATH):
    logger.error(f"Model file not found at {MODEL_PATH}")
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response, 204
        
    logger.info("Received upload request")
    logger.debug(f"Request files: {request.files}")
    logger.debug(f"Request headers: {request.headers}")
    
    if 'video' not in request.files:
        logger.error("No video file in request")
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No selected file'}), 400
    
    logger.info(f"Received file: {file.filename}")
    
    if not allowed_file(file.filename):
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type. Only video files are allowed'}), 400

    # Delete all existing files in the upload folder
    logger.info("Cleaning up existing files")
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                logger.debug(f"Deleted existing file: {filename}")
        except Exception as e:
            logger.error(f'Error deleting {file_path}: {e}')

    # Save the new file
    filename = file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        # Ensure the upload folder exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save the file
        file.save(file_path)
        
        # Verify the file was saved
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"Successfully saved file: {filename} (Size: {file_size} bytes)")
            response = jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'size': file_size
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            raise Exception("File was not saved successfully")
            
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

@app.route('/detect', methods=['GET', 'OPTIONS'])
def detect_video():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 204
        
    logger.info("Received detection request")
    logger.debug(f"Request headers: {request.headers}")
    
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        error_msg = f"Model file not found at {MODEL_PATH}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500
    
    # Get the latest uploaded video
    if not os.path.exists(UPLOAD_FOLDER):
        error_msg = "Upload folder not found"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 400
    
    files = os.listdir(UPLOAD_FOLDER)
    if not files:
        error_msg = "No uploaded videos found"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 400
    
    latest_video = files[0]  # Since we only keep one file at a time
    # Construct the relative path from the service directory to the uploaded file
    video_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, latest_video))
   
    
    logger.info(f"Looking for video at path: {video_path}")
    logger.info(f"Absolute path: {os.path.abspath(video_path)}")
    
    if not os.path.exists(video_path):
        error_msg = f"Video file not found at {video_path}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 400
    
    try:
        logger.info(f"Starting detection for video: {latest_video}")
        logger.info(f"Video path: {video_path}")
        logger.info(f"Model path: {MODEL_PATH}")
        
        # Add a small delay to ensure file system sync
        import time
        time.sleep(1)
        
        prediction = detect_fake_video(video_path)
        logger.info(f"Raw prediction result: {prediction}")
        
        if prediction is None:
            error_msg = "Detection failed - no prediction returned"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500
            
        result = {
            'is_real': bool(prediction[0]),
            'confidence': float(prediction[1])
        }
        
        logger.info(f"Detection completed: {result}")
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    except Exception as e:
        error_msg = f"Error during detection: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        response = jsonify({'error': error_msg})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 500

if __name__ == '__main__':
    logger.info("Starting Flask server")
    logger.info(f"Model path: {MODEL_PATH}")
    logger.info(f"Model exists: {os.path.exists(MODEL_PATH)}")
    logger.info(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    app.run(debug=True, host='0.0.0.0', port=5000)
