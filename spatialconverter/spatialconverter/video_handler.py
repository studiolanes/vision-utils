import logging
import numpy as np
import scipy
import cv2
import os
from transformers import pipeline, Pipeline
from PIL import Image, ImageChops
from moviepy.editor import ImageSequenceClip, VideoFileClip
from torch.multiprocessing import Pool, Process, set_start_method, cpu_count
from collections import namedtuple
from typing import List
from spatialconverter.file_mixin import FileMixin
from spatialconverter.timer import timing

set_start_method("spawn", force=True)


FrameData = namedtuple("FrameData", ["index", "frame"])


class VideoHandler(FileMixin):
    def __init__(self, filename, fps=30):
        self.filename = filename
        self.directory = None
        self.pipe = None
        self.fps = fps

    def over_under_video_filename(self):
        return f"{self.get_directory_name()}/over_under.mp4"

    def spatial_video_filename(self):
        return f"{self.get_directory_name()}/spatial_video.mov"

    def spatial_audio_filename(self):
        return f"{self.get_directory_name()}/temp-audio.m4a"

    def get_pipe(self) -> Pipeline:
        """
        Taken from https://github.com/DepthAnything/Depth-Anything-V2. Note that we use the
        depth-anything-v2-small-hf model because it runs faster since it's a small model. Feel
        free to swap out this model with the larger one if you want a higher quality output.
        We also haven't change any of the parameters and that could improve the estimation as well.
        """
        if self.pipe is None:
            # Main depth estimation model
            self.pipe = pipeline(
                task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf"
            )
        return self.pipe

    @timing
    def produce_frames(self):
        """Return a list of frames that we can processing on 1 by 1"""
        capture = cv2.VideoCapture(self.filename)
        frame_idx = 0
        result = []
        while True:
            frame_idx += 1
            return_code, frame = capture.read()
            if not return_code:
                break
            frame_tuple = (frame, frame_idx)
            result.append(frame_tuple)
        return result

    def shift_image(self, data, shift_amount=10):
        # Ensure depth image is grayscale (for single value)
        data_with_alpha = np.dstack(
            [data, np.full(data.shape[:2], 255, dtype=np.uint8)]
        )
        frame = Image.fromarray(data_with_alpha, "RGBA")
        frame_depth = self.get_pipe()(frame)["depth"]
        depth_image = frame_depth.convert("L")
        depth_data = np.array(depth_image)
        deltas = np.array((depth_data / 255.0) * float(shift_amount), dtype=int)

        shifted_data = np.zeros_like(data_with_alpha)

        width = frame.width

        for y, row in enumerate(deltas):
            width = len(row)
            x = 0
            while x < width:
                dx = row[x]
                if x + dx >= width:
                    break
                if x - dx < 0:
                    shifted_data[y][x - dx] = [0, 0, 0, 0]
                else:
                    shifted_data[y][x - dx] = data_with_alpha[y][x]
                x += 1

        # Convert the pixel data to an image.
        shifted_image = Image.fromarray(shifted_data)

        alphas_image = Image.fromarray(
            scipy.ndimage.binary_fill_holes(
                ImageChops.invert(shifted_image.getchannel("A"))
            )
        ).convert("1")
        shifted_image.putalpha(ImageChops.invert(alphas_image))
        return shifted_image

    def inpaint(self, image):
        org_image = np.array(image)
        damaged_image = np.array(image)

        # Convert all pixels greater than zero to black while black becomes white
        # Assuming damaged_image is a NumPy array of shape (height, width, 3)
        mask = damaged_image.sum(axis=2) > 0

        # Initialize a new array with the same shape as damaged_image, filled with white pixels
        new_image = np.ones_like(damaged_image) * 255
        new_image[mask] = [0, 0, 0]

        # saving the mask
        mask = cv2.cvtColor(new_image, cv2.COLOR_BGR2GRAY)
        inpainted = cv2.inpaint(org_image, mask, 3, cv2.INPAINT_NS)
        return inpainted

    def create_over_under_video_frame(self, frame) -> List[FrameData]:
        """Stack the converted images on the top and bottom of each other."""
        image, index = frame
        logging.info(f"frame: {index}")

        # Shift and inpaint images
        shifted_left_image = self.shift_image(image, 10).convert("RGB")
        inpainted_left_image = self.inpaint(shifted_left_image)
        shifted_right_image = self.shift_image(image, 50).convert("RGB")
        inpainted_right_image = self.inpaint(shifted_right_image)

        # Combine images over and under
        stacked_image = cv2.vconcat([inpainted_left_image, inpainted_right_image])
        stacked_image = cv2.cvtColor(stacked_image, cv2.COLOR_BGR2RGB)
        return FrameData(index, stacked_image)

    @timing
    def make_video(self):
        frames = self.produce_frames()
        logging.info(f"Processed {len(frames)} frames")

        # Use the number of cpus that your computer has. This doesn't work on all systems
        # but we're using this as an approximation to parallelize running on each frame
        multi_pool = Pool(processes=cpu_count())
        output = multi_pool.map(self.create_over_under_video_frame, frames)
        multi_pool.close()
        multi_pool.join()

        # Since we parallelized this, let's re-sort the frames by the index
        sorted_frames = sorted(output, key=lambda x: x.index)
        clip = ImageSequenceClip([obj.frame for obj in sorted_frames], fps=self.fps)
        video_clip = VideoFileClip(self.filename)
        audio = video_clip.audio
        clip = clip.set_audio(audio)
        clip.write_videofile(
            self.over_under_video_filename(),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=self.spatial_audio_filename(),
            remove_temp=True,
        )

        logging.info("Running OS process")
        command = f"./spatial make -i {self.over_under_video_filename()} -f ou -o {self.spatial_video_filename()} --args ./iPhone15Pro.args"
        os.system(command)
