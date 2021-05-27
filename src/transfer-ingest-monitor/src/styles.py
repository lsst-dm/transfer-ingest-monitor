import os

from jinja2 import Template

css = ''
with open(os.path.join(os.path.dirname(__file__), "style.css")) as f:
    css = f.read()

with open(os.path.join(os.path.dirname(__file__), "templates/head.tpl.html")) as f:
    templateText = f.read()
template = Template(templateText)
html_head = template.render(
    css=css,
)
