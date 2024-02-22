import logging
from transformers import pipeline, Pipeline
from PIL import Image, ImageChops
import numpy as np
import scipy
import cv2
from depthmodels.timer import timing
from moviepy.editor import ImageSequenceClip
from torch.multiprocessing import Pool, Process, set_start_method, cpu_count
from collections import namedtuple
from typing import List
from depthmodels.file_mixin import FileMixin

set_start_method("spawn", force=True)


FrameData = namedtuple("FrameData", ["index", "frame"])


class VideoHandler(FileMixin):
    def __init__(self, filename, fps=30):
        self.filename = filename
        self.directory = None
        self.pipe = None
        self.fps = fps

    def video_pathname(self):
        return f"{self.get_directory_name()}/spatial_video.mp4"

    def get_pipe(self) -> Pipeline:
        """
        Taken from https://github.com/LiheYoung/Depth-Anything. Note that we use the
        depth-anything-small-hf model because it runs faster since it's a small model. Feel
        free to swap out this model with the larger one if you want a higher quality output.
        We also haven't change any of the parameters and that could improve the estimation as well.
        """
        if self.pipe is None:
            # Main depth estimation model
            self.pipe = pipeline(
                task="depth-estimation", model="LiheYoung/depth-anything-small-hf"
            )
        return self.pipe

    @timing
    def produce_frames(self):
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

    @timing
    def shift_image(self, data, shift_amount=10):
        # Ensure depth image is grayscale (for single value)
        data_with_alpha = np.dstack(
            [data, np.full(data.shape[:2], 255, dtype=np.uint8)]
        )
        frame = Image.fromarray(data_with_alpha, "RGBA")
        frame_depth = self.get_pipe()(frame)["depth"]
        depth_img = frame_depth.convert("L")
        depth_data = np.array(depth_img)
        deltas = np.array((depth_data / 255.0) * float(shift_amount), dtype=int)

        # This creates the transprent resulting image.
        # For now, we're dealing with pixel data.
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

    @timing
    def shift_and_inpaint(self, img, amount):
        shifted = self.shift_image(img, shift_amount=amount).convert("RGB")
        org_img = np.array(shifted)
        damaged_img = np.array(shifted)

        # Converting all pixels greater than zero to black while black becomes white
        # Assuming damaged_img is a NumPy array of shape (height, width, 3)
        # Calculate the sum along the color channels (axis=2) and compare if greater than 0
        mask = damaged_img.sum(axis=2) > 0

        # Initialize a new array with the same shape as damaged_img, filled with white pixels
        new_img = np.ones_like(damaged_img) * 255
        new_img[mask] = [0, 0, 0]

        # saving the mask
        mask = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
        dst = cv2.inpaint(org_img, mask, 3, cv2.INPAINT_NS)
        return dst

    @timing
    def create_over_under_video_frame(self, frame) -> List[FrameData]:
        image, index = frame
        logging.info(f"frame: {index}")
        left_img = self.shift_and_inpaint(image, 10)
        right_img = self.shift_and_inpaint(image, 50)

        stacked_img = cv2.vconcat([left_img, right_img])  # Combine images side by side
        stacked_img = cv2.cvtColor(stacked_img, cv2.COLOR_BGR2RGB)
        return FrameData(index, stacked_img)

    @timing
    def make_video(self):
        frames = self.produce_frames()
        logging.info(f"Process frames {len(frames)}")

        # Use the number of cpus that your computer has. This doesn't work on all systems
        # but we're using this as an approximation to parallelize running on each frame
        multi_pool = Pool(processes=cpu_count())
        output = multi_pool.map(self.create_over_under_video_frame, frames[:10])
        multi_pool.close()
        multi_pool.join()

        # Since we parallelized this, let's re-sort the frames by the index
        sorted_frames = sorted(output, key=lambda x: x.index)
        clip = ImageSequenceClip([obj.frame for obj in sorted_frames], fps=self.fps)
        clip.write_videofile(self.video_pathname(), codec="libx264", audio=False)
