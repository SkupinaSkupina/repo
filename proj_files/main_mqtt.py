import tkinter as tk
from tkinter import filedialog
from threading import Thread, Event
import cv2
from PIL import Image, ImageTk
import torch
import winsound
import paho.mqtt.client as mqtt
from datetime import datetime
from prometheus_client import start_http_server, Counter, Gauge
import psutil
import time

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yolo Object Detection Prototype")
        self.root.geometry('1200x800')

        # Styling variables
        bg_color = "#353535"
        accent_color = "#535353"
        text_color = "#FFFFFF"
        button_color = "darkcyan"

        self.root.config(bg=bg_color)

        # Create and place the widgets
        self.select_button = tk.Button(root, text="Select Video", command=self.select_video_file,
                                       bg=button_color, fg=text_color, font=('Helvetica', 12, 'bold'))
        self.select_button.pack(pady=10)

        self.webcam_button = tk.Button(root, text="Load Camera", command=self.load_webcam_stream,
                                       bg=button_color, fg=text_color, font=('Helvetica', 12, 'bold'))
        self.webcam_button.pack(pady=10)

        self.source_label = tk.Label(root, text="No video selected", bg=bg_color, fg=text_color)
        self.source_label.pack(pady=5)

        # Frame information
        self.frame_info_label = tk.Label(root, text="Frame: 0/0", bg=bg_color, fg=text_color)
        self.frame_info_label.pack(pady=5)

        # Main frame
        self.main_frame = tk.Frame(root, bg=bg_color, borderwidth=0, highlightthickness=0)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights
        for i in range(4):
            self.main_frame.grid_rowconfigure(i, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=3)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Canvas for video output
        self.canvas = tk.Canvas(self.main_frame, width=800, height=450, bg="#202020", borderwidth=0,
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=3, columnspan=3, padx=20, pady=20, sticky='nsew')

        # Text frame
        text_frame = tk.Frame(self.main_frame, bg=bg_color)
        text_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20))

        # Text boxes
        self.proximity_text_box = self.create_text_box(text_frame, height=10, width=65, side=tk.LEFT)
        self.text_box = self.create_text_box(text_frame, height=10, width=30)
        self.area_text_box = self.create_text_box(text_frame, height=10, width=30)

        self.initialize_textboxes()

        self.cap = None

        # Load YOLOv5 model, using GPU if available
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5custom.pt').to(self.device)

        # Coordinates of the line
        self.line_y = 450  # Adjust this value as needed
        self.line_color = (255, 0, 0)  # Red color

        # Define colors for different classes
        self.class_colors = {
            'person': (255, 0, 0),  # Red
            'ball': (0, 255, 255),  # Yellow
            'tree': (0, 255, 0),  # Green
            'car': (0, 0, 255)  # Blue
        }

        # Initialize beep control
        self.beep_event = Event()
        self.min_distance = float('inf')

        # Start the beep thread
        self.beep_thread = Thread(target=self.beep_control)
        self.beep_thread.start()

        # Initialize MQTT
        self.broker = "10.8.5.3"
        self.port = 1883
        self.topic = "/data"
        self.producer = mqtt.Client(client_id="Alen", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.producer.connect(self.broker, self.port, 60)
        self.producer.loop_start()

        # Prometheus metrics
        self.counter_sending = Counter('sending_counter', 'Number of messages sent')
        self.bytes_sending = Counter('bytes_sending_counter', 'Number of bytes sent')
        self.cpu_usage_gauge = Gauge('cpu_usage', 'CPU usage of the application')
        self.ram_usage_gauge = Gauge('ram_usage', 'RAM usage of the application')
        self.fps_gauge = Gauge('fps', 'Frames per second')
        self.cars_detected_gauge = Gauge('cars_detected', 'Number of cars detected in the current frame')
        self.persons_detected_gauge = Gauge('persons_detected', 'Number of persons detected in the current frame')
        self.trees_detected_gauge = Gauge('trees_detected', 'Number of trees detected in the current frame')
        self.balls_detected_gauge = Gauge('balls_detected', 'Number of balls detected in the current frame')

        # Define counters for detected object classes
        self.object_counters = {
            'person': Counter('person_detected_total', 'Total number of people detected'),
            'ball': Counter('ball_detected_total', 'Total number of balls detected'),
            'tree': Counter('tree_detected_total', 'Total number of trees detected'),
            'car': Counter('car_detected_total', 'Total number of cars detected')
        }

        # Define counter for incidents
        self.incident_counter = Counter('incident_total', 'Total number of incidents')

        # Previous counts to track changes
        self.previous_counts = {
            'person': 0,
            'ball': 0,
            'tree': 0,
            'car': 0
        }

        # Start Prometheus metrics server
        start_http_server(8000)

        # Start monitoring thread
        self.start_monitoring()

    def create_text_box(self, parent, height, width, side=tk.LEFT):
        """Create and return a text box with given parameters."""
        text_box = tk.Text(parent, state=tk.DISABLED, height=height, width=width, bg="#535353", fg="#FFFFFF",
                           wrap=tk.WORD)
        text_box.pack(side=side, padx=(0, 10))
        return text_box

    def initialize_textboxes(self):
        for textbox in [self.text_box, self.area_text_box, self.proximity_text_box]:
            textbox.config(state=tk.NORMAL)
            textbox.delete('1.0', tk.END)
            textbox.insert(tk.END, "Ready to load video...\n")
            textbox.config(state=tk.DISABLED)

    def select_video_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mov")])
        if file_path:
            self.source_label.config(text=file_path)
            self.run_detection(file_path)

    def load_webcam_stream(self):
        self.source_label.config(text="Webcam Stream")
        self.run_detection(0)  # 0 default webcam index

    def run_detection(self, source):
        # Open video source
        self.cap = cv2.VideoCapture(source)

        # Check if the video is opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video.")
            return

        # Get the total number of frames in the video
        if isinstance(source, str):  # Only get frame count for video files
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            self.total_frames = float('inf')  # For webcam, we don't have a known total frame count

        # Run detection in a separate thread to keep the GUI responsive
        Thread(target=self.process_frame).start()

    def process_frame(self):
        passed_frames = 0
        start_time = time.time()

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            passed_frames += 1

            # Size of video frame
            frame = cv2.resize(frame, (800, 450))

            # Perform object detection
            results = self.model(frame, size=640)

            # Filter results
            detected_classes = results.pred[0][:, -1].cpu().numpy()
            detected_boxes = results.pred[0][:, :4].cpu().numpy()
            detected_confidences = results.pred[0][:, 4].cpu().numpy()

            # Generate unique names for each detected object
            object_names = self.generate_object_names(detected_classes)

            # Update GUI with detected objects
            objects_count = {self.model.names[int(cls)]: list(detected_classes).count(cls) for cls in set(detected_classes)}
            self.update_textbox(objects_count)

            # Update Prometheus counters
            self.update_prometheus_counters(objects_count)

            # Update the gauges with the number of detected objects
            self.update_gauges(objects_count)

            # Calculate and update bounding box areas
            bounding_box_areas = self.calculate_areas(detected_boxes)
            self.update_area_textbox(bounding_box_areas, object_names)

            # Draw bounding boxes with unique names and line at the bottom
            frame = self.draw_bounding_boxes(frame, detected_boxes, detected_classes, object_names)

            # Convert frame to ImageTk format and update canvas
            self.update_canvas(frame)

            # Update frame info label
            if self.total_frames != float('inf'):  # Only update frame info for video files
                self.frame_info_label.config(text=f"Frame: {passed_frames}/{self.total_frames}")
            else:
                self.frame_info_label.config(text=f"Frame: {passed_frames}")

            # Calculate and update FPS
            elapsed_time = time.time() - start_time
            fps = passed_frames / elapsed_time if elapsed_time > 0 else 0
            self.fps_gauge.set(fps)

            # Sleep
            self.root.update_idletasks()
            self.root.update()

        self.cap.release()
        cv2.destroyAllWindows()

    def generate_object_names(self, detected_classes):
        # Dynamically create the name count dictionary based on model class names
        name_count = {name: 0 for name in self.model.names}
        object_names = []
        for cls in detected_classes:
            name = self.model.names[int(cls)]
            if name not in name_count:
                name_count[name] = 0
            name_count[name] += 1
            object_names.append(f"{name}{name_count[name]}")
        return object_names

    def draw_bounding_boxes(self, frame, filtered_boxes, filtered_classes, object_names):
        messages = []
        min_distance = float('inf')
        for box, cls, name in zip(filtered_boxes, filtered_classes, object_names):
            x1, y1, x2, y2 = map(int, box)
            class_name = self.model.names[int(cls)]
            color = self.class_colors[class_name]

            # Draw bounding box
            frame = cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Draw object name
            frame = cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            # Draw line at the bottom
            cv2.line(frame, (0, self.line_y), (frame.shape[1], self.line_y), self.line_color, 1)
            # Calculate distance from object to line
            bottom_center = ((x1 + x2) // 2, y2)
            distance = abs(bottom_center[1] - self.line_y)
            min_distance = min(min_distance, distance)
            # Display distance
            frame = cv2.putText(frame, f"{distance} px", bottom_center, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Determine message based on fixed distance
            if distance < 50:
                messages.append(f"Stop immediately! {name} is too close!")
                overlay = frame.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
                self.proximity_text_box.config(state=tk.DISABLED, fg="red", bg="#535353")
                self.send_incident_alert(name)  # Send MQTT alert and update incident counter
            elif 50 <= distance < 100:
                messages.append(f"Warning! Pay attention to {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="orange", bg="#535353")
            elif 100 <= distance < 150:
                messages.append(f"Getting close to {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="yellow", bg="#535353")
            elif 150 <= distance < 250:
                messages.append(f"Approaching {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="lime", bg="#535353")

        self.update_proximity_textbox(messages)
        self.min_distance = min_distance
        self.beep_event.set()  # Trigger beep event
        return frame

    def update_proximity_textbox(self, messages):
        self.proximity_text_box.config(state=tk.NORMAL)
        self.proximity_text_box.delete('1.0', tk.END)
        for message in messages:
            self.proximity_text_box.insert(tk.END, f"{message}\n")
        self.proximity_text_box.config(state=tk.DISABLED)

    def update_canvas(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)

        # Calculate offsets to center the image
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = imgtk.width(), imgtk.height()
        x_offset = (canvas_width - img_width) // 2
        y_offset = (canvas_height - img_height) // 2

        self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk

    def update_textbox(self, objects_count):
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete('1.0', tk.END)
        for name, count in objects_count.items():
            self.text_box.insert(tk.END, f"{name}: {count}\n")
        self.text_box.config(state=tk.DISABLED)

    def update_area_textbox(self, bounding_box_areas, object_names):
        self.area_text_box.config(state=tk.NORMAL)
        self.area_text_box.delete('1.0', tk.END)
        for name, area in zip(object_names, bounding_box_areas):
            self.area_text_box.insert(tk.END, f"{name} Area: {area:.2f} px\n")
        self.area_text_box.config(state=tk.DISABLED)

    def calculate_areas(self, boxes):
        areas = []
        for box in boxes:
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)
            areas.append(area)
        return areas

    def update_prometheus_counters(self, objects_count):
        for object_class, count in objects_count.items():
            if object_class in self.object_counters:
                increment = count - self.previous_counts[object_class]
                if increment > 0:
                    self.object_counters[object_class].inc(increment)
                self.previous_counts[object_class] = count
                print(f"{object_class} counter: {self.object_counters[object_class]._value.get()}")

    def update_gauges(self, objects_count):
        self.cars_detected_gauge.set(objects_count.get('car', 0))
        self.persons_detected_gauge.set(objects_count.get('person', 0))
        self.trees_detected_gauge.set(objects_count.get('tree', 0))
        self.balls_detected_gauge.set(objects_count.get('ball', 0))

    def send_incident_alert(self, object_name):
        message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Incident occurred with {object_name}!"
        self.producer.publish(self.topic, message, qos=1, retain=False)
        self.counter_sending.inc()
        self.bytes_sending.inc(len(message.encode('utf-8')))
        self.incident_counter.inc()
        print(f"MQTT Incident Alert Sent: {message}")
        print(f"Incident counter: {self.incident_counter._value.get()}")

    # Starts a thread to monitor CPU, RAM usage, and FPS.
    def start_monitoring(self):
        def monitor():
            while True:
                # Update CPU and RAM usage as a percentage
                process = psutil.Process()
                self.cpu_usage_gauge.set(process.cpu_percent(interval=1))
                self.ram_usage_gauge.set(process.memory_percent())  # RAM usage in percentage

                time.sleep(1)

        Thread(target=monitor, daemon=True).start()

    def beep_control(self):
        while True:
            self.beep_event.wait()
            self.beep_event.clear()
            beep_interval = None
            if self.min_distance < 50:
                beep_interval = 0.1
            elif self.min_distance < 75:
                beep_interval = 0.4
            elif self.min_distance < 100:
                beep_interval = 0.75
            elif self.min_distance < 125:
                beep_interval = 1
            elif self.min_distance < 150:
                beep_interval = 1.5
            elif self.min_distance < 175:
                beep_interval = 2

            if beep_interval:
                print(f"Beeping with interval: {beep_interval} seconds")
                while self.min_distance < 175:
                    winsound.Beep(1000, int(beep_interval * 1000))  # 1000 Hz frequency, duration in ms
                    self.beep_event.wait(timeout=beep_interval)
                    #print("Beep")

# Setup the main window
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()