from transformers import pipeline
from PIL import Image, ImageChops
from pathlib import Path
import random
import string
import os
import logging
import numpy as np
import scipy
import cv2
from depthmodels.file_mixin import FileMixin


class ImageHandler(FileMixin):
    def __init__(self, filename: str):
        self.filename = filename
        self.directory = None

    def depth_image_filename(self):
        return f"{self.get_directory_name()}/depth_image.jpg"

    def left_image_filename(self):
        return f"{self.get_directory_name()}/stereo_left.png"

    def right_image_filename(self):
        return f"{self.get_directory_name()}/stereo_right.png"

    def output_filename(self):
        return f"{self.get_directory_name()}/output.heic"

    def generate_depth_image(self):
        """Generate a depth image and save it in a folder inside a newgg folder.

        Update the pipeline information below to use different models.
        See https://huggingface.co/docs/transformers/main/en/model_doc/depth_anything for other
        possible models, e.g. "LiheYoung/depth-anything-small-hf"
        """
        logging.info("Generating depth image. This might take long...")
        pipe = pipeline(
            task="depth-estimation", model="LiheYoung/depth-anything-large-hf"
        )
        image = Image.open(self.filename)
        depth_image = pipe(image)["depth"]
        logging.info(f"Saved new file {self.depth_image_filename()}")
        depth_image.save(self.depth_image_filename())
        return depth_image

    def shift_image(self, depth_image, shifted_image_filename, shift_amount=10):
        """
        Copied from https://medium.com/@damngoodtech/creating-3d-stereo-images-from-2d-images-using-invokeai-4245902abef5.
        Worth optimizing more and setting shift amounts based on your binocular disparity.
        """
        image = Image.open(self.filename)
        image = image.convert("RGBA")
        data = np.array(image)

        depth_image = depth_image.convert("L")
        depth_data = np.array(depth_image)
        deltas = np.array((depth_data / 255.0) * float(shift_amount), dtype=int)

        shifted_data = np.zeros_like(data)

        width = image.width

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
                    shifted_data[y][x - dx] = data[y][x]
                x += 1

        shifted_image = Image.fromarray(shifted_data)

        alphas_image = Image.fromarray(
            scipy.ndimage.binary_fill_holes(
                ImageChops.invert(shifted_image.getchannel("A"))
            )
        ).convert("1")
        shifted_image.putalpha(ImageChops.invert(alphas_image))

        logging.info(f"Shifted {shifted_image_filename}")
        shifted_image.save(shifted_image_filename)

        return shifted_image

    def inpaint_image(self, shifted_image_filename):
        original_image = cv2.imread(filename=shifted_image_filename)
        damaged_image = cv2.imread(filename=shifted_image_filename)

        height, width = damaged_image.shape[0], damaged_image.shape[1]

        # Converting all pixels greater than zero to black while black becomes white
        for i in range(height):
            for j in range(width):
                if damaged_image[i, j].sum() > 0:
                    damaged_image[i, j] = 0
                else:
                    damaged_image[i, j] = [255, 255, 255]

        mask = cv2.cvtColor(damaged_image, cv2.COLOR_BGR2GRAY)
        inpainted_image = cv2.inpaint(original_image, mask, 3, cv2.INPAINT_NS)

        logging.info(f"Inpainted {shifted_image_filename}")
        cv2.imwrite(shifted_image_filename, inpainted_image)

    def make_3d_image(self):
        depth_image = self.generate_depth_image()

        # left image
        self.shift_image(depth_image, self.left_image_filename(), 10)
        self.inpaint_image(self.left_image_filename())

        # right image
        self.shift_image(depth_image, self.right_image_filename(), 50)
        self.inpaint_image(self.right_image_filename())

        # Run OS process
        logging.info("Running OS process")
        command = f"../../result/Products/usr/local/bin/picCombiner -l {self.left_image_filename()} -r {self.right_image_filename()} -o {self.output_filename()}"
        os.system(command)
