from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import requests
import time
import hashlib

app = Flask(__name__)
model = load_model('waste-classification.h5')

classify_interval = 6  # Adjust the interval as needed in seconds
last_classify_time = time.time()
last_image_hash = None

ESP32_CAM_IP = "http://192.168.74.50"  # Static IP address of your ESP32-CAM

# Function to preprocess a frame for model prediction
def preprocess_frame(frame):
    frame = cv2.resize(frame, (160, 160))
    frame = frame.astype('float32') / 255.0
    frame = np.expand_dims(frame, axis=0)
    return frame

# Function to classify waste from a frame
def classify_waste(frame):
    processed_frame = preprocess_frame(frame)
    prediction = model.predict(processed_frame)
    class_label = 'Organik' if prediction[0][0] > 0.5 else 'Anorganik'
    return class_label

# Function to calculate hash of an image
def calculate_image_hash(image):
    image_data = cv2.imencode('.jpg', image)[1].tobytes()
    return hashlib.md5(image_data).hexdigest()

# Generator function to stream video frames
def generate_frames():
    while True:
        try:
            img_resp = requests.get(ESP32_CAM_IP + "/cam", stream=True)
            img_resp.raise_for_status()
            frame = np.frombuffer(img_resp.content, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (240, 240))  # Resize captured frame to match display size
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_resp.content + b'\r\n\r\n')
        except Exception as e:
            print(f"Error fetching frame: {e}")
            continue

# Endpoint for video feed
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Endpoint for waste classification
@app.route('/classify_image', methods=['POST'])
def classify_image():
    global last_classify_time, last_image_hash
    
    current_time = time.time()
    if current_time - last_classify_time < classify_interval:
        print("Waiting to classify...")
        return "Waiting to classify..."
    
    # Read image from request
    file_bytes = np.asarray(bytearray(request.data), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    # Calculate image hash
    current_image_hash = calculate_image_hash(img)
    print(f"Current Image Hash: {current_image_hash}")
    print(f"Last Image Hash: {last_image_hash}")

    if current_image_hash == last_image_hash:
        print("Image has not changed.")
        return "Image has not changed."

    # Update last image hash
    last_image_hash = current_image_hash
    
    # Classify waste
    class_label = classify_waste(img)
    print(f"Classified as: {class_label}")

    if class_label == 'Organik':
        response = "O"  # Signal for organic waste
    else:
        response = "I"  # Signal for inorganic waste

    # Update last classify time
    last_classify_time = current_time

    # Send classification to ESP32
    try:
        requests.post(f"{ESP32_CAM_IP}/classify_image", data=response, headers={'Content-Type': 'text/plain'})
    except Exception as e:
        print(f"Error sending classification to ESP32: {e}")

    return response

# Main route to render HTML template
@app.route('/')
def index():
    return render_template('web.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)