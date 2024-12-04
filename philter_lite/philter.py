import re
import warnings
from dataclasses import dataclass
from typing import Dict, List

import nltk

from philter_lite.coordinate_map import PUNCTUATION_MATCHER, CoordinateMap

from .filters import Filter, PosFilter, RegexContextFilter, RegexFilter, SetFilter

DEFAULT_PHI_TYPE_LIST = [
    "DATE",
    "Patient_Social_Security_Number",
    "Email",
    "Provider_Address_or_Location",
    "Age",
    "Name",
    "OTHER",
]

REGEX_NON_ALPHANUM_CHAR = re.compile(r"[^a-zA-Z0-9]")
REGEX_NON_ALPHANUM_GROUP = re.compile(r"[^a-zA-Z0-9]+")
REGEX_WHITESPACES = re.compile(r"(\s+)")
REGEX_ALL = re.compile(".")


@dataclass(frozen=True)
class PhiEntry:
    start: int
    stop: int
    word: str
    phi_type: str


@dataclass(frozen=True)
class NonPhiEntry:
    start: int
    stop: int
    word: str
    filepath: str


@dataclass(frozen=True)
class DataTracker:
    text: str
    phi: List[PhiEntry]
    non_phi: List[NonPhiEntry]


def detect_phi(
    text_data: str,
    patterns: List[Filter],
    phi_type_list: List[str] = DEFAULT_PHI_TYPE_LIST,
):
    """Run the set or regex on the input data, generating a coordinate map of hits given.

    (this performs a dry run on the data and doesn't transform)
    """
    # create coordinate maps for each pattern
    pattern_coords = {}
    for pat in patterns:
        pattern_coords[pat.title] = CoordinateMap()

    # Get full self.include/exclude map before transform
    data_tracker = DataTracker(text_data, [], [])

    # create an intersection map of all coordinates we'll be removing
    exclude_map = CoordinateMap()

    # create an interestion map of all coordinates we'll be keeping
    include_map = CoordinateMap()

    # add file to phi_type_dict
    phi_type_dict = {}
    for phi_type in phi_type_list:
        phi_type_dict[phi_type] = CoordinateMap()

    # Also add "OTHER" type for filters that aren't appropriately labeled
    phi_type_dict["OTHER"] = CoordinateMap()

    pos_list = _get_pos(text_data)

    # Create initial self.exclude/include for file
    for pat in patterns:
        pattern_coord = pattern_coords[pat.title]

        if pat.type == "regex" and isinstance(pat, RegexFilter):
            _map_regex(text=text_data, coord_map=pattern_coord, pattern=pat)
        elif pat.type == "set" and isinstance(pat, SetFilter):
            _map_set(pos_list=pos_list, coord_map=pattern_coord, pattern=pat)
        elif pat.type == "regex_context" and isinstance(pat, RegexContextFilter):
            _map_regex_context(
                text=text_data,
                coord_map=pattern_coord,
                all_patterns=pattern_coords,
                include_map=include_map,
                pattern=pat,
            )
        elif pat.type == "pos_matcher" and isinstance(pat, PosFilter):
            _map_parts_of_speech(pos_list=pos_list, coord_map=pattern_coord, pattern=pat)
        elif pat.type == "match_all":
            _match_all(text=text_data, coord_map=pattern_coord)
        else:
            raise Exception("Error, pattern type not supported: ", pat.type)
        _get_exclude_include_maps(
            pat,
            text_data,
            pattern_coord,
            include_map,
            exclude_map,
            phi_type_dict,
            data_tracker,
        )

    # create intersection maps for all phi types and add them to a dictionary containing all maps
    # get full exclude map (only updated either on-command by map_regex_context or at the very end of map_
    # coordinates)
    # full_exclude_map = include_map.get_complement(text_data)

    for phi_type in phi_type_list:
        for start, stop in phi_type_dict[phi_type].filecoords():
            data_tracker.phi.append(
                PhiEntry(
                    start=start,
                    stop=stop,
                    word=text_data[start:stop],
                    phi_type=phi_type,
                )
            )

    return include_map, exclude_map, data_tracker


def _get_pos(text):
    cleaned = _get_clean(text)
    return nltk.pos_tag(cleaned)


def _get_clean(text, pre_process=REGEX_NON_ALPHANUM_CHAR):
    # Use pre-process to split sentence by spaces AND symbols, while preserving spaces in the split list
    lst = REGEX_WHITESPACES.split(text)
    cleaned = []
    for item in lst:
        if len(item) > 0:
            if not item.isspace():
                split_item = REGEX_WHITESPACES.split(pre_process.sub(" ", item))
                for elem in split_item:
                    if len(elem) > 0:
                        cleaned.append(elem)
            else:
                cleaned.append(item)
    return cleaned


def _map_regex(
    text,
    pattern: RegexFilter,
    coord_map: CoordinateMap,
    pre_process=REGEX_NON_ALPHANUM_CHAR,
) -> CoordinateMap:
    """Create a coordinate map from the pattern on this data.

    Generates a coordinate map of hits given (dry run doesn't transform).
    """
    regex = pattern.data

    # All regexes except matchall
    if regex != REGEX_ALL:
        matches = regex.finditer(text)

        for m in matches:
            coord_map.add_extend(m.start(), m.start() + len(m.group()))

        return coord_map

    # MATCHALL/CATCHALL
    else:
        # Split note the same way we would split for set or POS matching
        matchall_list = REGEX_WHITESPACES.split(text)
        matchall_list_cleaned = []
        for item in matchall_list:
            if len(item) > 0:
                if not item.isspace():
                    split_item = REGEX_WHITESPACES.split(pre_process.sub(" ", item))
                    for elem in split_item:
                        if len(elem) > 0:
                            matchall_list_cleaned.append(elem)
                else:
                    matchall_list_cleaned.append(item)

        start_coordinate = 0
        for word in matchall_list_cleaned:
            start = start_coordinate
            stop = start_coordinate + len(word)
            word_clean = REGEX_NON_ALPHANUM_GROUP.sub("", word.lower().strip())
            if len(word_clean) == 0:
                # got a blank space or something without any characters or digits, move forward
                start_coordinate += len(word)
                continue

            if regex.match(word_clean):
                coord_map.add_extend(start, stop)

            # advance our start coordinate
            start_coordinate += len(word)

        return coord_map


def _map_regex_context(
    text,
    pattern: RegexContextFilter,
    coord_map: CoordinateMap,
    all_patterns: Dict[str, CoordinateMap],
    include_map: CoordinateMap,
    pre_process=REGEX_NON_ALPHANUM_CHAR,
) -> CoordinateMap:
    """Create a CoordinateMap from combined regex + PHI coordinates of all previously mapped patterns."""
    regex = pattern.data
    context = pattern.context
    try:
        context_filter = pattern.context_filter
    except KeyError:
        warnings.warn(
            f"deprecated missing context_filter field in filter {pattern.title} of "
            f"type regex_context, assuming 'all'",
            DeprecationWarning,
        )
        context_filter = "all"

    # Get PHI coordinates
    if context_filter == "all":
        current_include_map = include_map
        # Create complement exclude map (also excludes punctuation)
        full_exclude_map = current_include_map.get_complement(text)

    else:
        full_exclude_map_coordinates = all_patterns[context_filter]
        full_exclude_map = {}
        for start, stop in full_exclude_map_coordinates.filecoords():
            full_exclude_map[start] = stop

    # 1. Get coordinates of all include and exclude mathches
    # 2. Find all patterns expressions that match regular expression
    matches = regex.finditer(text)
    for m in matches:
        # initialize phi_left and phi_right
        phi_left = False
        phi_right = False

        match_start = m.span()[0]
        match_end = m.span()[1]

        # PHI context left and right
        phi_starts = []
        phi_ends = []
        for start in full_exclude_map:
            phi_starts.append(start)
            phi_ends.append(full_exclude_map[start])

        if match_start in phi_ends:
            phi_left = True

        if match_end in phi_starts:
            phi_right = True

        # Get index of m.group()first alphanumeric character in match
        tokenized_matches = []
        match_text = m.group()
        split_match = REGEX_WHITESPACES.split(pre_process.sub(" ", match_text))

        # Get all spans of tokenized match (because remove() function requires tokenized start coordinates)
        coord_tracker = 0
        for element in split_match:
            if element != "":
                if not PUNCTUATION_MATCHER.match(element[0]):
                    current_start = match_start + coord_tracker
                    current_end = current_start + len(element)
                    tokenized_matches.append((current_start, current_end))

                    coord_tracker += len(element)
                else:
                    coord_tracker += len(element)

        # Check for context, and add to coordinate map
        if (
            (context == "left" and phi_left is True)
            or (context == "right" and phi_right)
            or (context == "left_or_right" and (phi_right or phi_left))
            or (context == "left_and_right" and (phi_right and phi_left))
        ):
            for item in tokenized_matches:
                coord_map.add_extend(item[0], item[1])

    return coord_map


def _match_all(text, coord_map: CoordinateMap) -> CoordinateMap:
    """Simply map to the entirety of the file."""
    # add the entire length of the file
    coord_map.add(0, len(text))
    return coord_map


def _map_set(pos_list, coord_map: CoordinateMap, pattern: SetFilter) -> CoordinateMap:
    """Create a coordinate mapping of words any words in this set."""
    set_data = pattern.data

    # get part of speech we will be sending through this set
    # note, if this is empty we will put all parts of speech through the set
    check_pos = False
    pos_set = pattern.pos
    if len(pos_set) > 0:
        check_pos = True

    start_coordinate = 0
    for tup in pos_list:
        word = tup[0]
        pos = tup[1]
        start = start_coordinate
        stop = start_coordinate + len(word)

        # This converts spaces into empty strings, so we know to skip forward to the next real word
        word_clean = REGEX_NON_ALPHANUM_GROUP.sub("", word.lower().strip())
        if len(word_clean) == 0:
            # got a blank space or something without any characters or digits, move forward
            start_coordinate = stop
            continue

        if not check_pos or (check_pos and pos in pos_set):
            if word_clean in set_data or word in set_data:
                coord_map.add_extend(start, stop)

        # advance our start coordinate
        start_coordinate = stop

    return coord_map


def _map_parts_of_speech(pos_list, pattern: PosFilter, coord_map: CoordinateMap) -> CoordinateMap:
    """Create a coordinate mapping of words which match this part of speech (POS)."""
    pos_set = set(pattern.pos)

    # Use pre-process to split sentence by spaces AND symbols, while preserving spaces in the split list

    start_coordinate = 0
    for tup in pos_list:
        word = tup[0]
        pos = tup[1]
        start = start_coordinate
        stop = start_coordinate + len(word)
        word_clean = REGEX_NON_ALPHANUM_GROUP.sub("", word.lower().strip())
        if len(word_clean) == 0:
            # got a blank space or something without any characters or digits, move forward
            start_coordinate += len(word)
            continue

        if pos in pos_set:
            coord_map.add_extend(start, stop)

        # advance our start coordinate
        start_coordinate += len(word)

    return coord_map


def _get_exclude_include_maps(
    pattern: Filter,
    txt,
    coord_map: CoordinateMap,
    include_map: CoordinateMap,
    exclude_map: CoordinateMap,
    phi_type_dict: Dict[str, CoordinateMap],
    data_tracker: DataTracker,
):
    exclude = pattern.exclude
    filter_path = pattern.title
    if pattern.phi_type:
        phi_type = pattern.phi_type
    else:
        phi_type = "OTHER"

    for start, stop in coord_map.filecoords():
        if pattern.type != "regex_context":
            if exclude:
                if not include_map.does_overlap(start, stop):
                    exclude_map.add_extend(start, stop)
                    phi_type_dict[phi_type].add_extend(start, stop)

            else:
                if not exclude_map.does_overlap(start, stop):
                    include_map.add_extend(start, stop)
                    data_tracker.non_phi.append(
                        NonPhiEntry(
                            start=start,
                            stop=stop,
                            word=txt[start:stop],
                            filepath=filter_path,
                        )
                    )

        # Add regex_context to map separately
        else:
            if exclude:
                exclude_map.add_extend(start, stop)
                include_map.remove(start, stop)
                phi_type_dict[phi_type].add_extend(start, stop)
            else:
                include_map.add_extend(start, stop)
                exclude_map.remove(start, stop)
                data_tracker.non_phi.append(
                    NonPhiEntry(
                        start=start,
                        stop=stop,
                        word=txt[start:stop],
                        filepath=filter_path,
                    )
                )
