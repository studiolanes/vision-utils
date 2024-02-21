
# 2d to Spatial photos

Convert any jpgs/pngs to spatial photos viewable in the Apple Vision Pro!

There is a mini swift cli executable that works on M1 apple computers to attach png files together.

See [Blog Post](https://blog.studiolanes.com/posts/2d-to-spatial-photos) for more info.


## First time installation/run

This assumes that you have [poetry](https://github.com/python-poetry/poetry).

```bash
cd depthmodels
poetry install
poetry shell
# Poetry breaks when trying to install from source, so do this the first time
pip install -q git+https://github.com/huggingface/transformers.git
cd depthmodels
# Swap the file path to your photo here
python main.py --file /Users/herk/Downloads/skydive.jpg
```
