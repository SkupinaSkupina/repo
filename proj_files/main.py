import winsound
from threading import Thread, Event, Lock
import time
import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import torch
import os
from datetime import datetime


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
        button_frame = tk.Frame(root, bg=bg_color)
        button_frame.pack(pady=10)

        self.select_button = tk.Button(button_frame, text="Select Video", command=self.select_video_file,
                                       bg=button_color, fg=text_color, font=('Helvetica', 12, 'bold'))
        self.select_button.grid(row=0, column=0, padx=5)

        self.webcam_button = tk.Button(button_frame, text="Load Camera", command=self.load_webcam_stream,
                                       bg=button_color, fg=text_color, font=('Helvetica', 12, 'bold'))
        self.webcam_button.grid(row=0, column=1, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_video,
                                     bg="red", fg=text_color, font=('Helvetica', 12, 'bold'))
        self.stop_button.grid(row=0, column=2, padx=5)

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
        self.stop_event = Event()

        # Load YOLOv5 model, using GPU if available
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5custom.pt').to(self.device)

        # Coordinates of the line
        self.line_y = 450  # Adjust this value as needed
        self.line_color = (255, 0, 0)  # Red color

        # Define colors for different classes
        self.class_colors = {
            'person': (255, 0, 0),  # Blue
            'ball': (0, 255, 255),  # Yellow
            'tree': (0, 255, 0),  # Green
            'car': (0, 0, 255)  # Red
        }

        # Initialize beep control
        self.beep_event = Event()
        self.beep_thread_lock = Lock()
        self.beep_thread_active = False
        self.current_beep_thread = None
        self.constant_beep_thread = None
        self.constant_beep_thread_active = False

        # Initialize recording control
        self.recording = False
        self.out = None
        self.log_data = []

        # Start the beep thread
        self.beep_thread = Thread(target=self.beep_control)
        self.beep_thread.daemon = True
        self.beep_thread.start()

    def create_text_box(self, parent, height, width, side=tk.LEFT):
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
        self.stop_event.clear()
        Thread(target=self.process_frame).start()

    def stop_video(self):
        # Stop the frame processing
        self.stop_event.set()

        # Save the recording if necessary
        if self.recording:
            self.stop_recording()

    def process_frame(self):
        passed_frames = 0

        while self.cap.isOpened() and not self.stop_event.is_set():
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
            objects_count = {self.model.names[int(cls)]: list(detected_classes).count(cls) for cls in
                             set(detected_classes)}
            self.update_textbox(objects_count)

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

            # Check if recording is enabled and if an incident occurred
            if self.record_incident_var.get() and self.min_distance < 50:
                if not self.recording:
                    self.start_recording(frame)
                self.log_data.append((passed_frames, self.text_box.get("1.0", tk.END), self.min_distance))

            if self.recording:
                self.out.write(frame)

            # Sleep
            self.root.update_idletasks()
            self.root.update()

        self.cap.release()
        cv2.destroyAllWindows()

        # Stop recording when video ends
        if self.recording:
            self.stop_recording()

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

    # ------------------------- beeping
    def beep_control(self):
        while True:
            self.beep_event.wait()
            self.beep_event.clear()
            self.manage_beep_thread()

    def manage_beep_thread(self):
        with self.beep_thread_lock:
            if self.min_distance < 50:
                if not self.constant_beep_thread_active or self.constant_beep_thread is None:
                    self.start_constant_beep_thread()
            else:
                if self.constant_beep_thread is not None:
                    self.stop_constant_beep_thread()
                beep_interval = self.calculate_beep_interval()
                if beep_interval is not None:
                    self.start_beep_thread(beep_interval)

    def calculate_beep_interval(self):
        if self.min_distance <= 50:
            return 0
        elif self.min_distance <= 75:
            return 0.005
        elif self.min_distance <= 100:
            return 0.09
        elif self.min_distance <= 125:
            return 0.2
        elif self.min_distance <= 150:
            return 0.4
        return None

    def start_beep_thread(self, beep_interval):
        self.stop_beep_thread()  # Ensure no other thread is running
        self.beep_thread_active = True
        self.current_beep_thread = Thread(target=self.beep_in_loop, args=(beep_interval,))
        self.current_beep_thread.daemon = True
        self.current_beep_thread.start()

    def stop_beep_thread(self):
        self.beep_thread_active = False
        if self.current_beep_thread is not None:
            self.current_beep_thread.join()
            self.current_beep_thread = None

    def beep_in_loop(self, interval):
        while self.beep_thread_active and self.min_distance <= 150:
            winsound.Beep(900, 200)  # 900 Hz frequency, 0.2s duration
            time.sleep(interval)

    def start_constant_beep_thread(self):
        self.stop_beep_thread()  # Ensure no other thread is running
        self.constant_beep_thread_active = True
        self.constant_beep_thread = Thread(target=self.constant_beep)
        self.constant_beep_thread.daemon = True
        self.constant_beep_thread.start()

    def stop_constant_beep_thread(self):
        self.constant_beep_thread_active = False
        if self.constant_beep_thread is not None:
            self.constant_beep_thread.join()
            self.constant_beep_thread = None

    def constant_beep(self):
        while self.constant_beep_thread_active and self.min_distance < 50:
            winsound.Beep(900, 1000)  # 900 Hz frequency, 1s duration


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()