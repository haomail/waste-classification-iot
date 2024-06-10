from flask import Flask, render_template, Response, request
import cv2
import numpy as np
import requests
import time

app = Flask(__name__)
previous_frame = None
last_processed_time = 0
process_interval = 1  # Adjusted interval time in seconds


ESP32_CAM_IP = "http://192.168.xx.93"  # Change this to the IP address of your ESP32-CAM

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture_image')
def capture_image():
    response = requests.get(ESP32_CAM_IP + "/capture_image")
    return response.content

def gen():
    while True:
        try:
            img_resp = requests.get(ESP32_CAM_IP + "/cam", stream=True)
            img_resp.raise_for_status()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_resp.content + b'\r\n\r\n')
        except Exception as e:
            print(f"Error fetching image: {e}")
            continue

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

def process_image(data):
    global previous_frame
    global last_processed_time

    # Check if the processing interval has passed
    current_time = time.time()
    if current_time - last_processed_time < process_interval:
        return "160"  # Return center position (160) if the interval is too short

    try:
        file_bytes = np.asarray(bytearray(request.data), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if previous_frame is None:
            previous_frame = gray
            return "160"  # Center position when no previous frame

        frame_delta = cv2.absdiff(previous_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            previous_frame = gray
            print("No object detected.")
            return "160"  # Return center position if no contours are found
        
        largest_contour = max(contours, key=cv2.contourArea)
        (x, y, w, h) = cv2.boundingRect(largest_contour)
        
        object_position = x + w // 2
        previous_frame = gray
        last_processed_time = current_time
        
        angle = int((object_position / 320.0) * 180)
        print(f"Object detected at position {object_position}, moving servo to {angle} degrees")
        
        return str(object_position)

    except Exception as e:
        print(f"Error processing image: {e}")
        return "160"
    
@app.route('/process_image', methods=['POST'])
def process_image_endpoint():
    if request.method == 'POST':
        data = request.data
        position = process_image(data)
        return position
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)