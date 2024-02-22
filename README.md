```
 __   _(_)___(_) ___  _ __    _   _| |_(_) |___
 \ \ / / / __| |/ _ \| '_ \  | | | | __| | / __|
  \ V /| \__ \ | (_) | | | | | |_| | |_| | \__ \
   \_/ |_|___/_|\___/|_| |_|  \__,_|\__|_|_|___/
```
# vision-utils

This repo contains various projects related to the Vision Pro & visionOS.

## Contents

- [Convert 2D Photo to Spatial Photo](./spatialconverter/)
- [CLI to generate a stereoscopic image](./picCombiner)
- [visionOS Icons](./icons)

## 2D to Spatial Photo
Convert any jpgs/pngs to spatial photos viewable in the Apple Vision Pro! There is a mini swift cli executable that works on M1 apple computers to attach png files together.

See [Blog Post](https://blog.studiolanes.com/posts/2d-to-spatial-photos) for more info.

### Dependencies
We borrow the executable and iphone args from [Mike Swanson](https://blog.mikeswanson.com/spatial) for converting over under videos to spatial videos.

We also assume that you have [poetry](https://github.com/python-poetry/poetry) globally installed for python packaging.

```bash
cd spatialconverter
poetry install
poetry shell
# Poetry breaks when trying to install transformers from source, so run this installation the first time
pip install -q git+https://github.com/huggingface/transformers.git
```

### Subsequent runs

```bash
cd spatialconverter/spatialconverter
poetry shell
python main.py --photo /Users/herk/Downloads/photo.png
# python main.py --video /Users/herk/Downloads/skydive.mp4
```