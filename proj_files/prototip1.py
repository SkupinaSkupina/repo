import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import cv2
import torch
from threading import Thread

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yolo object detection prototype")

        # Create and place the widgets
        self.select_button = tk.Button(root, text="Select Video", command=self.select_video_file)
        self.select_button.pack(pady=10)

        self.source_label = tk.Label(root, text="No video selected")
        self.source_label.pack(pady=5)

        self.canvas = tk.Canvas(root, width=640, height=360)
        self.canvas.pack(side=tk.LEFT)

        self.frame_info_label = tk.Label(root, text="Frame: 0/0")
        self.frame_info_label.pack(pady=5, side=tk.LEFT)

        self.text_box = tk.Text(root, state=tk.DISABLED, height=10, width=30)
        self.text_box.pack(side=tk.TOP, padx=10, pady=10)

        self.area_text_box = tk.Text(root, state=tk.DISABLED, height=10, width=30)
        self.area_text_box.pack(side=tk.BOTTOM, padx=10, pady=10)

        self.initialize_textboxes()

        self.cap = None

        # Load YOLOv5 model with custom weights, using GPU if available
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5custom.pt').to(self.device)

    def initialize_textboxes(self):
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete('1.0', tk.END)
        self.text_box.insert(tk.END, "Ball: 0\n")
        self.text_box.insert(tk.END, "Car: 0\n")
        self.text_box.insert(tk.END, "Person: 0\n")
        self.text_box.insert(tk.END, "Tree: 0\n")
        self.text_box.config(state=tk.DISABLED)

        self.area_text_box.config(state=tk.NORMAL)
        self.area_text_box.delete('1.0', tk.END)
        self.area_text_box.config(state=tk.DISABLED)

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
        passed_frames = 0

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            passed_frames += 1

            # Resize frame to 640x360 (16:9) for performance
            frame = cv2.resize(frame, (640, 360))

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

            # Calculate and update bounding box areas
            bounding_box_areas = self.calculate_areas(detected_boxes)
            self.update_area_textbox(bounding_box_areas, object_names)

            # Draw bounding boxes with unique names
            frame = self.draw_bounding_boxes(frame, detected_boxes, detected_classes, object_names)

            # Convert frame to ImageTk format and update canvas
            self.update_canvas(frame)

            # Update frame info label
            self.frame_info_label.config(text=f"Frame: {passed_frames}/{self.total_frames}")

            # Sleep
            self.root.update_idletasks()
            self.root.update()

        self.cap.release()
        cv2.destroyAllWindows()

    def generate_object_names(self, filtered_classes):
        name_count = {"ball": 0, "car": 0, "person": 0, "tree": 0}
        object_names = []
        for cls in filtered_classes:
            name = self.model.names[int(cls)]
            name_count[name] += 1
            object_names.append(f"{name}{name_count[name]}")
        return object_names

    def draw_bounding_boxes(self, frame, filtered_boxes, filtered_classes, object_names):
        colors = {
            "ball": (0, 0, 255),    # Red
            "car": (255, 0, 0),     # Blue
            "person": (0, 255, 0),  # Green
            "tree": (255, 255, 0)   # Cyan
        }
        for box, cls, name in zip(filtered_boxes, filtered_classes, object_names):
            x1, y1, x2, y2 = map(int, box)
            color = colors[self.model.names[int(cls)]]
            frame = cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            frame = cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

    def update_canvas(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk

    def update_textbox(self, objects_count):
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete('1.0', tk.END)
        ball_count = objects_count.get("ball", 0)
        car_count = objects_count.get("car", 0)
        person_count = objects_count.get("person", 0)
        tree_count = objects_count.get("tree", 0)
        self.text_box.insert(tk.END, f"Ball: {ball_count}\n")
        self.text_box.insert(tk.END, f"Car: {car_count}\n")
        self.text_box.insert(tk.END, f"Person: {person_count}\n")
        self.text_box.insert(tk.END, f"Tree: {tree_count}\n")
        self.text_box.config(state=tk.DISABLED)

    def update_area_textbox(self, bounding_box_areas, object_names):
        self.area_text_box.config(state=tk.NORMAL)
        self.area_text_box.delete('1.0', tk.END)
        for name, area in zip(object_names, bounding_box_areas):
            self.area_text_box.insert(tk.END, f"{name} Area: {area:.3f} px\n")
        self.area_text_box.config(state=tk.DISABLED)

    def calculate_areas(self, boxes):
        areas = []
        for box in boxes:
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)
            areas.append(area)
        return areas

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoApp(root)
    root.mainloop()
