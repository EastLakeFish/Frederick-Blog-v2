# README

© 2026, frederickyang.com & eastlakefish.com. All rights reserved.

This repository contains the source code and content for my personal website, built with VitePress.

The website serves as a collection of notes, articles, research logs, and technical documentation. Most content is written in Markdown and organized hierarchically using directories. Navigation pages are generated automatically from the repository structure, eliminating the need for manually maintained navigation menus.

## Structure

Content is organized as a tree of directories.

```text
root/
├── .vitepress/  # config, components & styling
├── docs/  # source files & documentation
# notes
├── group-level/  # e.g. notes
│   └── topic-level/  # e.g. machine-learning
│       └── series-level/  # e.g. efficient-imagenet
│           └── note-level/  # e.g. sharding-imagenet
│               ├── assets/
│               ├── content-xxx  # e.g. 10, 20, 30
│               └── index.md
├── deploy.py  # deploy to nginx
#... (other files)
```

Each directory containing an index.md file represents a page on the website, which usually possesses a file for ordering.

## License & Permissions

See [license](https://frederickyang.com/license.html) page for details.