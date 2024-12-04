import os
import re
import subprocess
import sys

from nltk.tag.stanford import StanfordNERTagger

from philter_lite.coordinate_map import CoordinateMap

from . import NerFilter


def build_ner_tagger(classifier, tagger_jar, download: bool = True) -> StanfordNERTagger:
    if not os.path.exists(classifier) and not download:
        raise Exception("Filepath does not exist", classifier)
    else:
        # download the ner data
        process = subprocess.Popen("cd generate_dataset && ./download_ner.sh".split(), stdout=subprocess.PIPE)
        process.communicate()

    if not os.path.exists(tagger_jar):
        raise Exception("Filepath does not exist", tagger_jar)

    return StanfordNERTagger(classifier, tagger_jar)


def map_ner(
    text,
    pattern: NerFilter,
    coord_map: CoordinateMap,
    stanford_ner_tagger: StanfordNERTagger,
    pre_process=r"[^a-zA-Z0-9]+",
) -> CoordinateMap:
    """Map NER tagging."""
    pos_set = set()
    if pattern.pos:
        pos_set = set(pattern.pos)

    lst = re.split(r"(\s+)", text)
    cleaned = []
    for item in lst:
        if len(item) > 0:
            cleaned.append(item)

    ner_no_spaces = stanford_ner_tagger.tag(cleaned)
    # get our ner tags
    ner_set = {}
    for tup in ner_no_spaces:
        ner_set[tup[0]] = tup[1]
    ner_set_with_locations = {}
    start_coordinate = 0
    for w in cleaned:
        if w in ner_set:
            ner_set_with_locations[w] = (ner_set[w], start_coordinate)
        start_coordinate += len(w)

    # for the text, break into words and mark POS
    # with the parts of speech labeled, match any of these to our coordinate
    # add these coordinates to our coordinate map
    start_coordinate = 0
    for word in cleaned:
        word_clean = re.sub(pre_process, "", word.lower().strip())
        if len(word_clean) == 0:
            # got a blank space or something without any characters or digits, move forward
            start_coordinate += len(word)
            continue

        if word in ner_set_with_locations:
            ner_tag = ner_set_with_locations[word][0]
            start = ner_set_with_locations[word][1]
            if ner_tag in pos_set:
                stop = start + len(word)
                coord_map.add_extend(start, stop)
                sys.stdout.write(f"FOUND: {word}  NER: {ner_tag} {start} {stop}")

        # advance our start coordinate
        start_coordinate += len(word)

    return coord_map
