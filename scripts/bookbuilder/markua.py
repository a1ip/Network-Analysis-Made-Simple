#!/usr/bin/env python
# coding: utf-8

# # An attempt at writing a script that can convert every specified file to LeanPub Flavoured Markdown for publication on LeanPub

# In[ ]:


from lib import read_mkdocs


# In[ ]:


from pyprojroot import here


# In[ ]:


mkdocs_config = read_mkdocs()
nav = mkdocs_config["nav"]
docroot = here() / "docs"


# In[ ]:


from lib import parse_navigation

# The goal here is to flatten the tree structure into a list of 2-tuples,
# where the title is the first element and the filename is the second element.
title_files = parse_navigation(nav, [])
title_files.insert(0, ('Preface', 'preface/preface.md'))
title_files


# In[ ]:


from lib import exclude

exclusion = [
    "Welcome", 
    "Get Setup",
    "Prerequisites",
    "Further Learning",
    "Style Guide",
]

title_files = exclude(title_files, titles=exclusion)


# In[ ]:


title_files


# We now need to convert each of the files into Markua.

# In[ ]:


strings = ["df.head()", "another_thing\ndf2.head()"]


def replace_dataframe_with_markdown(s: str):
    new_string = ""
    for line in s.split("\n"):
        if (line.endswith(".head()") 
            or line.endswith(".describe()")
            or line.endswith("correlation_centrality(graphs[0])")
            or line.endswith("find_connected_persons(G, 'p2', 'c10')")
           ):
            line = f"print({line}.to_markdown())"
        new_string += line + "\n"
    return new_string

# replace_dataframe_head_with_markdown(strings[0])


# In[ ]:


def replace_render_html_with_raw(s: str):
    new_string = ""
    for line in s.split("\n"):
        if line.startswith("render_html"):
            line = line.replace("render_html", "")[1:-1]
        new_string += line + "\n"
    return new_string


# In[ ]:


def replace_admonition(src: str):
    
    if src.startswith("???"):
        new_text = ""
        for line in src.split("\n"):    
            if line.startswith("???"):
                line = "*Note:*"
            line = line.replace("    ", "")
            new_text += line + "\n"
        return new_text
    return src

text = """??? note "Geospatial Viz"

    As the creator of `nxviz`,
    I would recommend using proper geospatial packages
    to build custom geospatial graph viz,
    such as [`pysal`](http://pysal.org/).)
    
    That said, `nxviz` can probably do what you need
    for a quick-and-dirty view of the data.
"""

print(replace_admonition(text))


# In[ ]:


def replace_markdown_table_tabs(body: str):
    return body.replace("    |", "|")


# In[ ]:


from nbconvert.exporters import MarkdownExporter
from nbformat.notebooknode import NotebookNode
from nbconvert.preprocessors import ExecutePreprocessor
from lib import strip_execution_count

def nb2markdown(nb: NotebookNode, kernel: str):
    """
    Compile final notebook into a single PDF while executing it.

    :param nb: The compiled notebook object with all notebook cells.
    :param kernel: String name of the kernel to output.
    """
    # Convert all `.head()` to `.head().to_markdown()`
    # before execution
    for i, cell in enumerate(nb["cells"]):
        src = nb["cells"][i]["source"]
        src = (
            src
            .replace("HTML(anim(G2, msg, n_frames=4).to_html5_video())", "# HTML(anim(G2, msg, n_frames=4).to_html5_video())")
        )
        src = replace_dataframe_with_markdown(src)
        src = replace_render_html_with_raw(src)
        src = replace_admonition(src)
        
        nb["cells"][i]["source"] = src

    ep = ExecutePreprocessor(timeout=600, kernel_name=kernel)
    ep.preprocess(nb)

    strip_execution_count(nb)
    pdf_exporter = MarkdownExporter()
    body, resources = pdf_exporter.from_notebook_node(nb)
    return body, resources


# In[ ]:


from lib import read_notebook


# In[ ]:


sample_chapters = ["Preface", "Learning Goals", "Introduction to Graphs", "The NetworkX API"]


# In[ ]:


# Now, convert everything into plain text markdown.


# In[ ]:


from pathlib import Path
from pyprojroot import here

build_dir = here() / "manuscript"
build_dir.mkdir(parents=True, exist_ok=True)

images_dir = build_dir / "images"
images_dir.mkdir(parents=True, exist_ok=True)


# In[ ]:


def nth_repl_all(string: str, substring: str, replacement: str, nth: int) -> str:
    """Replace nth string with substring."""
    find = string.find(substring)
    # loop util we find no match
    i = 1
    while find != -1:
        # if i  is equal to nth we found nth matches so replace
        if i == nth:
            string = string[:find] + replacement + string[find + len(substring):]
            i = 0
        # find + len(sub) + 1 means we start after the last match
        find = string.find(substring, find + len(substring) + 1)
        i += 1
    return string


# In[ ]:


def mdlatex2lfmlatex(text):
    text = nth_repl_all(text, substring="$$", replacement="{@@}", nth=1)
    text = nth_repl_all(text, substring="$", replacement="{@@}", nth=1)
    text = nth_repl_all(text, substring="{@@}", replacement="{$$}", nth=1)
    text = nth_repl_all(text, substring="{$$}", replacement="{/$$}", nth=2)
    return text


# In[ ]:





# In[ ]:


import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

book_txt = ""
files_to_validate = []



for chapter, fpath_str in title_files:
    logging.info(f"Processing chapter {chapter}")
    fpath = Path(fpath_str)
    source_path = docroot / fpath
    # Handle notebooks
    if source_path.suffix == ".ipynb":
        text, resources = nb2markdown(read_notebook(source_path), kernel="nams")
    # Handle markdown files
    else:
        with open(source_path, "r+") as f:
            text = f.read()
        resources = dict()
        resources["outputs"] = dict()
        
    text = f"# {chapter}\n\n" + text

    if chapter in sample_chapters:
        insert = "{sample: true}\n\n"
        text = insert + text

    # More processing: Replace all output_* with <relative_dir>_md_<autogen_numbers>
    img_prefix = str(fpath.with_suffix(".md")).replace("/", "_").replace(".", "_") + "_"
    text = text.replace("output_", "images/" + img_prefix)

    # More processing: Leanpub Flavoured Markdown uses {$$} to delineate LaTeX.
    # text = text.replace("$$", "{$$}")
    text = mdlatex2lfmlatex(text)
    
    # More preprocessing: Clean up tabs for all of the markdown tables
    text = replace_markdown_table_tabs(text)

    markdown_dir = (build_dir / fpath).with_suffix(".md")
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the text out
    
    with open(markdown_dir / "index.md", "w+") as f:
        f.write(text)
    files_to_validate.append(markdown_dir /  "index.md")

    # Write the resources out
    for k, v in resources["outputs"].items():
        k = k.replace("output_", img_prefix)
        logging.debug(f"image filename = {k}")
        with open(images_dir / k, "wb") as f:
            f.write(v)
            
    book_txt = book_txt + str(fpath.with_suffix(".md") / "index.md") + "\n"


# In[ ]:


# hack to find all images embedded in markdown and copy it to manuscript/images
from shutil import copyfile
for image in docroot.glob('**/images/*.png'):
    copyfile(image, images_dir / image.name)


# In[ ]:


with open(build_dir / "Book.txt", "w+") as f:
    f.write(book_txt)


# In[ ]:


def has_html(s: str) -> bool:
    tag_openers = ["<li", "<ul", "<ol", "<span", "<p", "<em"]
    for tag in tag_openers:
        if tag in s:
            return True
    return False


# In[ ]:


# Print a line if it's got problems
for fpath in files_to_validate:
    with open(fpath, "r+") as f:
        for line in f.readlines():
            if line.startswith("    |"):
                print(fpath, line)
            if line.startswith("???"):
                print(fpath, line)
            if has_html(line):
                print(fpath, line)
            if " '|   |" in line:
                print(fpath, line)

