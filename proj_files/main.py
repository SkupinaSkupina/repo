import tkinter as tk
from tkinter import filedialog
from threading import Thread
import cv2
from PIL import Image, ImageTk
import torch
import numpy as np

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yolo Object Detection Prototype")
        self.root.geometry('1200x800')  # Increased size to accommodate new textbox

        # Styling variables
        bg_color = "#353535"  # Dark background for a modern look
        accent_color = "#535353"
        text_color = "#FFFFFF"
        button_color = "darkcyan"  # Accent color for buttons and highlights

        self.root.config(bg=bg_color)

        # Create and place the widgets
        self.select_button = tk.Button(root, text="Select Video", command=self.select_video_file,
                                       bg=button_color, fg=text_color, font=('Helvetica', 12, 'bold'))
        self.select_button.pack(pady=10)

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
        self.canvas = tk.Canvas(self.main_frame, width=800, height=450, bg="#202020", borderwidth=0, highlightthickness=0)
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
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True).to(self.device)

        # Coordinates of the line
        self.line_y = 450  # Adjust this value as needed
        self.line_color = (255, 0, 0)  # Red color

    def create_text_box(self, parent, height, width, side=tk.LEFT):
        """Create and return a text box with given parameters."""
        text_box = tk.Text(parent, state=tk.DISABLED, height=height, width=width, bg="#535353", fg="#FFFFFF", wrap=tk.WORD)
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

    def run_detection(self, source_file):
        # Open video source
        self.cap = cv2.VideoCapture(source_file)

        # Check if the video is opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video.")
            return

        # Get the total number of frames in the video
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Run detection in a separate thread to keep the GUI responsive
        Thread(target=self.process_frame).start()

    def process_frame(self):
        target_classes = [0, 2, 37]  # person, car, sports ball
        passed_frames = 0

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            passed_frames += 1

            # Resize frame to 800x450 (16:9) for performance
            frame = cv2.resize(frame, (800, 450))

            # Perform object detection
            results = self.model(frame, size=640)  # Ensure the model processes the resized frame

            # Filter results for specific classes
            detected_classes = results.pred[0][:, -1].cpu().numpy()
            detected_boxes = results.pred[0][:, :4].cpu().numpy()
            detected_confidences = results.pred[0][:, 4].cpu().numpy()

            filtered_boxes, filtered_confidences, filtered_classes = self.filter_detections(
                detected_classes, detected_boxes, detected_confidences, target_classes
            )

            # Generate unique names for each detected object
            object_names = self.generate_object_names(filtered_classes)

            # Update GUI with detected objects
            objects_count = {self.model.names[cls]: filtered_classes.count(cls) for cls in set(filtered_classes)}
            self.update_textbox(objects_count)

            # Calculate and update bounding box areas
            bounding_box_areas = self.calculate_areas(filtered_boxes)
            self.update_area_textbox(bounding_box_areas, object_names)

            # Draw bounding boxes with unique names and line at the bottom
            frame = self.draw_bounding_boxes(frame, filtered_boxes, filtered_classes, object_names)

            # Convert frame to ImageTk format and update canvas
            self.update_canvas(frame)

            # Update frame info label
            self.frame_info_label.config(text=f"Frame: {passed_frames}/{self.total_frames}")

            # Sleep
            self.root.update_idletasks()
            self.root.update()

        self.cap.release()
        cv2.destroyAllWindows()

    def filter_detections(self, detected_classes, detected_boxes, detected_confidences, target_classes):
        filtered_boxes = []
        filtered_confidences = []
        filtered_classes = []

        for i, cls in enumerate(detected_classes):
            if int(cls) in target_classes:
                filtered_boxes.append(detected_boxes[i])
                filtered_confidences.append(detected_confidences[i])
                filtered_classes.append(int(cls))

        return filtered_boxes, filtered_confidences, filtered_classes

    def generate_object_names(self, filtered_classes):
        name_count = {"person": 0, "car": 0, "sports ball": 0}
        object_names = []
        for cls in filtered_classes:
            name = self.model.names[cls]
            name_count[name] += 1
            object_names.append(f"{name}{name_count[name]}")
        return object_names

    def draw_bounding_boxes(self, frame, filtered_boxes, filtered_classes, object_names):
        messages = []
        for box, cls, name in zip(filtered_boxes, filtered_classes, object_names):
            x1, y1, x2, y2 = map(int, box)
            # Draw bounding box
            frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Draw object name
            frame = cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            # Draw line at the bottom
            cv2.line(frame, (0, self.line_y), (frame.shape[1], self.line_y), self.line_color, 1)
            # Calculate distance from object to line
            bottom_center = ((x1 + x2) // 2, y2)
            distance = abs(bottom_center[1] - self.line_y)
            # Display distance
            frame = cv2.putText(frame, f"{distance} px", bottom_center, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Determine message based on distance
            if distance < 50:
                messages.append(f"Stop immediately! {name} is too close!")
                self.proximity_text_box.config(state=tk.DISABLED, fg="white", bg="red")
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
            elif 70 <= distance < 100:
                messages.append(f"Warning! Pay attention to {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="orange", bg="#535353")
            elif 100 <= distance < 150:
                messages.append(f"Getting close to {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="yellow", bg="#535353")
            elif distance < 250:
                messages.append(f"Approaching {name}.")
                self.proximity_text_box.config(state=tk.DISABLED, fg="lime", bg="#535353")

        self.update_proximity_textbox(messages)
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

# Setup the main window
if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()
