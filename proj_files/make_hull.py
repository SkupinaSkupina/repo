import os
import cv2
import numpy as np
import torch
from skimage.filters import threshold_otsu
from yolov5 import YOLOv5

# Naloži YOLOv5 model
def load_model(model_path):
    model = YOLOv5(model_path, device='cpu')
    return model

# Zaznaj avtomobile z uporabo YOLOv5
def detect_cars(model, image):
    results = model.predict(image)  # Uporabi predict za pridobitev rezultatov
    car_bboxes = []
    for result in results.xyxy[0]:  # Iteriraj čez zaznane objekte
        if int(result[5]) == 2:     # Razred 2 predstavlja avtomobile v COCO podatkovni zbirki
            car_bboxes.append(result[:4].detach().cpu().numpy().astype(int))
    return car_bboxes

# Izlusci koordinate označenega dela (bounding box-a)
def extract_bbox(image, bbox):
    x1, y1, x2, y2 = bbox
    return image[y1:y2, x1:x2], (x1, y1)

# Uporabi barvne filtre
def apply_color_filters(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold_otsu(gray), 255, cv2.THRESH_BINARY)
    binary = cv2.bitwise_not(binary)  # Po potrebi invertiraj
    return binary

# Implementacija algoritma QuickHull
def quickhull(points):
    def find_hull(points, p1, p2):
        if not points:
            return []
        # Najdi tocko z najvecjo razdaljo od crte (p1, p2)
        distances = [np.cross(p2 - p1, point - p1) for point in points]
        max_index = np.argmax(distances)
        max_point = points[max_index]

        # Razdeli preostale tocke v dve podmnozici: levo od (p1, max_point) in levo od (max_point, p2)
        points1 = [point for point in points if np.cross(max_point - p1, point - p1) > 0]
        points2 = [point for point in points if np.cross(p2 - max_point, point - max_point) > 0]

        return find_hull(points1, p1, max_point) + [max_point] + find_hull(points2, max_point, p2)

    points = np.array(points)
    if len(points) < 3:
        return points
    min_point = points[np.argmin(points[:, 0])]
    max_point = points[np.argmax(points[:, 0])]

    left_set = [point for point in points if np.cross(max_point - min_point, point - min_point) > 0]
    right_set = [point for point in points if np.cross(max_point - min_point, point - min_point) < 0]

    return [min_point] + find_hull(left_set, min_point, max_point) + [max_point] + find_hull(right_set, max_point, min_point)

# Poisci konveksno lupino v binarni sliki
def find_convex_hull(binary_image):
    # Izvedi morfoloske operacije za ciscenje slike
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=1)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel, iterations=1)

    # Uporabi detekcijo robov
    edges = cv2.Canny(binary_image, 30, 100)
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        contours = [c for c in contours if cv2.contourArea(c) > 1000]  # Filtriraj majhne obrobe
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            points = np.squeeze(largest_contour)
            hull = np.array(quickhull(points))
        else:
            hull = np.array([])
    else:
        hull = np.array([])

    return hull, binary_image

# Prikaz konveksne lupine na originalni sliki
def overlay_convex_hull(original_image, hull, offset):
    hull_image = original_image.copy()
    if hull.size != 0:
        hull += offset  # Prilagodi koordinate lupine z offsetom
        cv2.polylines(hull_image, [hull], isClosed=True, color=(0, 255, 0), thickness=2)
    return hull_image

# Obdelaj video
def process_video(input_video_path, model_path, output_video_path, filtered_output_video_path):
    # Ustvari izhodni imenik, ce ne obstaja
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    os.makedirs(os.path.dirname(filtered_output_video_path), exist_ok=True)

    # Nalozi YOLO model
    model = load_model(model_path)
    # Odpri video
    cap = cv2.VideoCapture(input_video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
    filtered_out = cv2.VideoWriter(filtered_output_video_path, fourcc, fps, (frame_width, frame_height), isColor=False)

    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Zaznaj bounding boxe avtomobilov
        car_bboxes = detect_cars(model, frame)
        num_cars = len(car_bboxes)
        print(f"Frame: {frame_count} / {total_frames} | Cars: {num_cars}")

        if num_cars > 0:
            for bbox in car_bboxes:
                # Izlusci bounding box avtomobila
                car_image, offset = extract_bbox(frame, bbox)
                # Ustvari binarno sliko iz bounding box-a
                binary_image = apply_color_filters(car_image)
                # Poisci konveksno lupino
                hull, _ = find_convex_hull(binary_image)
                # Prikaz konveksne lupine na originalnem okvirju
                frame = overlay_convex_hull(frame, hull, np.array(offset))
                # Spremeni velikost binarne slike, da se ujema z originalno velikostjo okvirja
                binary_image_resized = cv2.resize(binary_image, (frame_width, frame_height))
                filtered_out.write(binary_image_resized)
        else:
            # Ce ni zaznanih avtomobilov, zapisi crni frame za filtrirani video
            filtered_out.write(np.zeros((frame_height, frame_width), dtype=np.uint8))

        # Zapisi frame v izhodni video
        out.write(frame)

    cap.release()
    out.release()
    filtered_out.release()
    print(f"Izhodni video shranjen kot {output_video_path}")
    print(f"Filtrirani izhodni video shranjen kot {filtered_output_video_path}")

if __name__ == "__main__":
    input_video_path = "videos/test_video.mp4"
    model_path = "yolov5n.pt"
    output_video_path = "videos/output_video.mp4"
    filtered_output_video_path = "videos/filtered_output_video.mp4"

    process_video(input_video_path, model_path, output_video_path, filtered_output_video_path)
