#!python3

# image tag patterns:
#   1. ![label](path)
#   2. <img .. src="path" .. />

import os
import re
import bs4
import click
import urllib.parse
from pathlib import Path
from typing import Iterator, Tuple
from collections import namedtuple

ImageEntry = namedtuple('ImageEntry', ['type', 'content', 'start', 'length'])
image_dir = None


def read_image_content(parent_dir: Path, url: str) -> bytes:
    import requests
    if urllib.parse.urlparse(str(url)).netloc != '':
        return requests.get(url).content
    else:
        if not Path(url).is_absolute():
            url = Path(parent_dir) / url

        return Path(url).read_bytes()


def parse_image_entries(s: str) -> Iterator[ImageEntry]:
    for match in re.finditer(r'(!\[.*?\]\(.*?\))|(<img.*?/>)', s):
        _type = 'markdown' if match.group()[0] == '!' else 'html'
        start = match.start()
        length = match.span()[1] - match.span()[0]
        content = match.group()
        yield ImageEntry(_type, content, start, length)


def process_entry(entry: ImageEntry, parent_dir: Path, image_dir: str) -> Tuple[Path, bytes, str]:
    img = None
    image_path = Path(image_dir)
    image_content = None
    source_image_path = None
    if entry.type == 'markdown':
        match = re.match(r'!\[(?P<label>.*?)\]\((?P<url>.*?)\)', entry.content)
        groupdict = match.groupdict()
        img = bs4.BeautifulSoup('<img>', 'lxml').img
        image_path /= Path(groupdict['url']).name
        source_image_path = groupdict['url']
        img['alt'] = groupdict['label']
        img['src'] = Path(os.path.relpath('.', parent_dir)) / image_path

    elif entry.type == 'html':
        img = bs4.BeautifulSoup(entry.content, 'lxml').img
        if match := re.search(r'src="(.*?)"', entry.content):
            source_image_path = match.group(1)
            image_path /= Path(match.group(1)).name
            img['src'] = Path(os.path.relpath('.', parent_dir)) / image_path
        else:
            raise ValueError('something wrong with the entry')

    image_content = read_image_content(parent_dir, source_image_path)
    return (image_path, image_content, str(img))


def convert(file: str, image_dir: str):
    s = Path(file).read_text()
    results = []
    index = 0
    for entry in parse_image_entries(s):
        skipped_content = s[index:entry.start]
        results.append(skipped_content)
        image_path, image_content, new_entry_string = process_entry(entry, Path(file).parent, image_dir)
        Path(image_path).write_bytes(image_content)
        results.append(new_entry_string)
        index = entry.start + entry.length

    results.append(s[index:])
    Path(file).write_text(''.join(results))


@click.command()
@click.option('--image-dir', default='image')
@click.argument('files', nargs=-1, type=click.Path(True))
def main(image_dir: str, files):
    image_dir = Path(image_dir)
    image_dir.mkdir(exist_ok=True)
    for file in files:
        convert(file, image_dir)


if __name__ == '__main__':
    main()
