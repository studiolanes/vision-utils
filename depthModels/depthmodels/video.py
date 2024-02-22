from transformers import pipeline
from PIL import Image, ImageChops
import numpy as np
import scipy
import cv2

from moviepy.editor import ImageSequenceClip

SAMPLE_FRAME = "sample.png"

PIPE = None


def get_pipe():
    # This will load the pipeline on demand on the current PROCESS/THREAD.
    # And load it only once.
    global PIPE
    if PIPE is None:
        PIPE = pipeline(
            task="depth-estimation", model="LiheYoung/depth-anything-small-hf"
        )
    return PIPE


def shift_image(data, shift_amount=10):
    # Ensure depth image is grayscale (for single value)
    data_with_alpha = np.dstack([data, np.full(data.shape[:2], 255, dtype=np.uint8)])
    frame = Image.fromarray(data_with_alpha, "RGBA")
    frame_depth = get_pipe()(frame)["depth"]
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


def shift_and_inpaint(img, amount):
    shifted = shift_image(img, shift_amount=amount).convert("RGB")
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


def create_over_under_video_frame(frame):
    image, idx = frame
    print("frame: ", idx)
    left_img = shift_and_inpaint(image, 10)
    right_img = shift_and_inpaint(image, 50)

    stacked_img = cv2.vconcat([left_img, right_img])  # Combine images side by side
    stacked_img = cv2.cvtColor(stacked_img, cv2.COLOR_BGR2RGB)
    return (idx, stacked_img)


def read_frames(path):
    cap = cv2.VideoCapture(VIDEO_PATH)
    frame_idx = 0

    while True:
        frame_idx += 1

        # Read a new frame
        ret, frame = cap.read()

        # If frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        yield (frame, frame_idx)


from torch.multiprocessing import Pool, Process, set_start_method

set_start_method("spawn", force=True)

if __name__ == "__main__":
    result = []

    VIDEO_PATH = "notebooks/sample.mov"
    cap = cv2.VideoCapture(VIDEO_PATH)
    frame_id = 0

    frames = list(read_frames(VIDEO_PATH))
    print("frames to be processed: ", len(frames))

    multi_pool = Pool(processes=10)
    output = multi_pool.map(create_over_under_video_frame, list(frames[:10]))
    multi_pool.close()
    multi_pool.join()

    fps = 30
    sorted_frames = sorted(output, key=lambda x: x[0])
    clip = ImageSequenceClip([obj[1] for obj in sorted_frames], fps=fps)
    video_path = "notebooks/new.mp4"
    clip.write_videofile(video_path, codec="libx264", audio=False)
