#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "camera_pins.h"

#define CAMERA_MODEL_AI_THINKER

const char* ssid = "trinitrotoluene";
const char* password = "albedoye";

WebServer server(80);
camera_config_t camera_config; // Declare camera_config as a global variable

void handleRoot() {
  server.send(200, "text/html", "<html><body><img src='/cam'></body></html>");
}

void handleCaptureImage() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Failed to capture image");
    server.send(500, "text/plain", "Failed to capture image");
    return;
  }

  WiFiClient client = server.client();
  client.write("HTTP/1.1 200 OK\r\n");
  client.write("Content-Type: image/jpeg\r\n");
  client.write("Content-Length: ");
  client.write(String(fb->len).c_str());
  client.write("\r\n\r\n");
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Start camera
  camera_config.ledc_channel = LEDC_CHANNEL_0;
  camera_config.ledc_timer = LEDC_TIMER_0;
  camera_config.pin_d0 = Y2_GPIO_NUM;
  camera_config.pin_d1 = Y3_GPIO_NUM;
  camera_config.pin_d2 = Y4_GPIO_NUM;
  camera_config.pin_d3 = Y5_GPIO_NUM;
  camera_config.pin_d4 = Y6_GPIO_NUM;
  camera_config.pin_d5 = Y7_GPIO_NUM;
  camera_config.pin_d6 = Y8_GPIO_NUM;
  camera_config.pin_d7 = Y9_GPIO_NUM;
  camera_config.pin_xclk = XCLK_GPIO_NUM;
  camera_config.pin_pclk = PCLK_GPIO_NUM;
  camera_config.pin_vsync = VSYNC_GPIO_NUM;
  camera_config.pin_href = HREF_GPIO_NUM;
  camera_config.pin_sccb_sda = SIOD_GPIO_NUM;
  camera_config.pin_sccb_scl = SIOC_GPIO_NUM;
  camera_config.pin_pwdn = PWDN_GPIO_NUM;
  camera_config.pin_reset = RESET_GPIO_NUM;
  camera_config.xclk_freq_hz = 10000000; // Lower frequency
  camera_config.frame_size = FRAMESIZE_QVGA; // 320x240 resolution
  camera_config.pixel_format = PIXFORMAT_JPEG; // for streaming
  camera_config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  camera_config.fb_location = CAMERA_FB_IN_PSRAM;
  camera_config.jpeg_quality = 15; // Higher value for lower quality
  camera_config.fb_count = 1; // Reduced frame buffer count

  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Start web server
  server.on("/", handleRoot);
  server.on("/cam", HTTP_GET, []() {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Failed to capture image");
      server.send(500, "text/plain", "Failed to capture image");
      return;
    }

    WiFiClient client = server.client();
    client.write("HTTP/1.1 200 OK\r\n");
    client.write("Content-Type: image/jpeg\r\n");
    client.write("Content-Length: ");
    client.write(String(fb->len).c_str());
    client.write("\r\n\r\n");
    client.write(fb->buf, fb->len);
    esp_camera_fb_return(fb);
  });
  server.on("/capture_image", HTTP_GET, handleCaptureImage);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
