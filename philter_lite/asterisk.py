import re

from .coordinate_map import CoordinateMap


def save_to_asterisk(contents, output_file):
    with open(output_file, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(contents)


def transform_text_asterisk(txt, include_map: CoordinateMap):
    last_marker = 0
    punctuation_matcher = re.compile(r"[^a-zA-Z0-9*]")
    # read the text by character, any non-punc non-overlaps will be replaced
    contents = []
    for i in range(len(txt)):

        if i < last_marker:
            continue

        if include_map.does_exist(i):
            # add our preserved text
            start, stop = include_map.get_coords(i)
            contents.append(txt[start:stop])
            last_marker = stop
        elif punctuation_matcher.match(txt[i]):
            contents.append(txt[i])
        else:
            contents.append("*")

    return "".join(contents)
