from flask import Flask, render_template, Response, request, jsonify
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np

model = load_model('waste-classification-120.h5')

app = Flask(__name__)

def preprocess_frame(frame):
    # Preprocess the frame for model prediction
    frame = cv2.resize(frame, (120, 120)) 
    frame = frame.astype('float32') / 255.0
    frame = np.expand_dims(frame, axis=0)  # Add batch dimension
    return frame

def generate_frames():
    camera = cv2.VideoCapture(0)  # Use 0 for webcam
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Preprocess the frame
            processed_frame = preprocess_frame(frame)
            # Predict
            prediction = model.predict(processed_frame)
            class_label = 'Organik' if prediction[0][0] > 0.5 else 'Anorganik'
            
            # Add prediction text to the frame
            cv2.putText(frame, class_label, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
