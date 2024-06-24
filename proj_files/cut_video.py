# Import necessary libraries
from moviepy.editor import VideoFileClip


# Function to change the frame rate of a video

def change_frame_rate(input_video_path, output_video_path, target_fps):
    # Load the video clip
    video = VideoFileClip(input_video_path)

    # Set the frame rate of the video
    video = video.set_fps(target_fps)

    # Write the result to a new video file
    video.write_videofile(output_video_path, fps=target_fps)


# Example usage
input_video_path = "data/video/video017_2.mp4"  # Path to your input video
output_video_path = "data/video/15_video017-2.mp4.mp4"  # Path to save the output video

# Change the frame rate of the video to x fps
fps = 15
change_frame_rate(input_video_path, output_video_path, fps)