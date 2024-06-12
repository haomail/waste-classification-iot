from flask import Flask, render_template, Response, request, jsonify
import requests
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
import io

app = Flask(__name__)

ESP32_CAM_IP = "http://192.168.56.93"  # Change this to the IP address of your ESP32-CAM

model = load_model('waste-classification.h5')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture_image')
def capture_image():
    response = requests.get(ESP32_CAM_IP + "/capture_image")
    image = Image.open(io.BytesIO(response.content))
    image = image.resize((160,160))
    image = np.array(image)
    image = np.expand_dims(image, axis=0)
    image = image / 255.0

    prediction = model.predict(image)
    class_names = ['Organik', 'Anorganik']
    predicted_class = class_names[np.argmax(prediction)]

    return jsonify({'class': predicted_class})
    # return response.content

def gen():
    while True:
        img_resp = requests.get(ESP32_CAM_IP + "/cam")
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img_resp.content + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)