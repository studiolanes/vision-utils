import argparse
import logging
import sys
from depthmodels.image_handler import ImageHandler
from depthmodels.video_handler import VideoHandler

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process 2D Photo")
    parser.add_argument("--photo", type=str, help="a file path to a photo")
    parser.add_argument("--video", type=str, help="a file path to a video")

    args = parser.parse_args()
    photo_filename = args.photo
    video_filename = args.video

    if photo_filename:
        image_handler = ImageHandler(photo_filename)
        image_handler.make_3d_image()
    elif video_filename:
        video_handler = VideoHandler(video_filename)
        video_handler.make_video()
    else:
        logging.info("Please add a photo or video if you want to see anything happen!")
