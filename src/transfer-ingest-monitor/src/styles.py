import os

css = ''
with open(os.path.join(os.path.dirname(__file__), "style.css")) as f:
    css = f.read()