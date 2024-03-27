import itertools
import re
from typing import List

PUNCTUATION_MATCHER = re.compile(r"[^a-zA-Z0-9*]")


class CoordinateMap:
    """Hits are stored in a coordinate map data structure

    This class stores start coordinates for any matches found for this pattern"""

    def __init__(self):
        """internal data structure maps filepaths to a map of int:string (coordinate start --> stop)

        map is the internal structure of
        { filename : { startcoordinate : stop_coordinate}}
        eg: { "data/foo.txt": {123:126, 19:25} }

        coord2pattern keeps reference of the patterns
        that matched this coorinate (can be multiple patterns)

        all_coords keeps a reference of all coordinates mapped by filename,
        allowing us to easily check if these coordinates have been matched yet"""

        self.map = {}
        self.coord2pattern = {}
        self.all_coords = {}

    def add(self, start, stop, overlap=False, pattern=""):
        """adds a new coordinate to the coordinate map

        if overlap is false, this will reject any overlapping hits (usually from multiple regex scan runs)
        """
        if not overlap:
            if self.does_overlap(start, stop):
                return False, "Error, overlaps were found: {} {}".format(start, stop)

        # add our start / stop coordinates
        self.map[start] = stop
        # add these coordinates to our all_coords map
        for i in range(start, stop):
            self.all_coords[i] = 1

        if pattern != "":
            self.add_pattern(start, stop, pattern)
        return True, None

    def add_pattern(self, start, stop, pattern):
        """adds this pattern to this start coord"""
        self.coord2pattern[start] = []
        self.coord2pattern[start].append(pattern)

    def add_extend(self, start, stop, pattern=""):
        """adds a new coordinate to the coordinate map
        if overlaps with another, will extend to the larger size"""
        overlaps = self.max_overlap(start, stop)

        def clear_overlaps(lst):
            for o in lst:
                self.remove(o["orig_start"], o["orig_end"])

        if len(overlaps) == 0:
            # no overlap, just save these coordinates
            self.add(start, stop, pattern=pattern, overlap=True)
        elif len(overlaps) == 1:
            clear_overlaps(overlaps)
            # 1 overlap, save this value
            o = overlaps[0]
            self.add(o["new_start"], o["new_stop"], pattern=pattern, overlap=True)
        else:
            clear_overlaps(overlaps)
            # greater than 1 overlap, by default this is sorted because of scan order
            o1 = overlaps[0]
            o2 = overlaps[-1]
            self.add(o2["new_start"], o1["new_stop"], pattern=pattern, overlap=True)

        return True, None

    def remove(self, start, stop):
        """Removes this coordinate pairing from the map, all_coords, and coord2pattern"""
        # delete from our map structure
        if start in self.map:
            del self.map[start]
        # delete any of these coordinates in our all_coords data structure
        for i in range(start, stop + 1):
            if i in self.all_coords:
                del self.all_coords[i]
        return True, None

    def scan(self):
        """does an inorder scan of the coordinates and their values"""
        for fn in self.map:
            coords = list(self.map[fn].keys())
            coords.sort()
            for coord in coords:
                yield fn, coord, self.map[fn][coord]

    def keys(self):
        for fn in self.map:
            yield fn

    def get_coords(self, start):
        stop = self.map[start]
        return start, stop

    def filecoords(self):
        """generator does an inorder scan of the coordinates for this file"""
        coords = sorted(self.map.keys())
        for coord in coords:
            yield coord, self.map[coord]

    def does_exist(self, index):
        """Simple check to see if this index is a hit (start of coordinates)"""
        if index in self.map:
            return True
        return False

    def does_overlap(self, start, stop):
        """Check if this coordinate overlaps with any existing range"""

        ranges = [list(range(key, self.map[key] + 1)) for key in self.map]
        all_coords = [item for sublist in ranges for item in sublist]
        # removing all_coords implementation until we write some tests
        for i in range(start, stop + 1):
            if i in all_coords:
                return True
        return False

    def calc_overlap(self, start, stop):
        """given a set of coordinates, will calculate all overlaps
        perf: stop after we know we won't hit any more
        perf: use binary search approach"""

        overlaps = []
        for s in self.map:
            e = self.map[s]
            if s >= start or s <= stop:
                # We found an overlap
                if e <= stop:
                    overlaps.append({"start": s, "stop": e})
                else:
                    overlaps.append({"start": s, "stop": stop})
            elif e >= start or e <= stop:
                if s >= start:
                    overlaps.append({"start": s, "stop": e})
                else:
                    overlaps.append({"start": start, "stop": e})
        return overlaps

    def max_overlap(self, start, stop):
        """given a set of coordinates, will calculate max of all overlaps
        perf: stop after we know we won't hit any more
        perf: use binary search approach"""

        overlaps = []
        for s in self.map:
            e = self.map[s]
            if s <= start <= e:
                # We found an overlap
                if stop >= e:
                    overlaps.append(
                        {
                            "orig_start": s,
                            "orig_end": e,
                            "new_start": s,
                            "new_stop": stop,
                        }
                    )
                else:
                    overlaps.append(
                        {"orig_start": s, "orig_end": e, "new_start": s, "new_stop": e}
                    )

            elif s <= stop <= e:
                if start <= s:
                    overlaps.append(
                        {
                            "orig_start": s,
                            "orig_end": e,
                            "new_start": start,
                            "new_stop": e,
                        }
                    )
                else:
                    overlaps.append(
                        {"orig_start": s, "orig_end": e, "new_start": s, "new_stop": e}
                    )

        return overlaps

    def get_complement(self, text):
        """get the complementary coordinates of the input coordinate map (excludes punctuation)"""

        complement_coordinate_map = {}

        current_map_coordinates: List[int] = []
        for start_key in self.map:
            start = start_key
            stop = self.map[start_key]
            current_map_coordinates += range(start, stop)

        text_coordinates = list(range(0, len(text)))
        complement_coordinates = list(
            set(text_coordinates) - set(current_map_coordinates)
        )

        # Remove punctuation from complement coordinates
        for i in range(0, len(text)):
            if PUNCTUATION_MATCHER.match(text[i]):
                if i in complement_coordinates:
                    complement_coordinates.remove(i)

        # Group complement coordinates into ranges
        def to_ranges(iterable):
            iterable = sorted(set(iterable))
            for key, group in itertools.groupby(
                enumerate(iterable), lambda t: t[1] - t[0]
            ):
                group_list = list(group)
                yield group_list[0][1], group_list[-1][1] + 1

        complement_coordinate_ranges = list(to_ranges(complement_coordinates))

        # Create complement dictionary
        for tup in complement_coordinate_ranges:
            start = tup[0]
            stop = tup[1]
            complement_coordinate_map[start] = stop

        return complement_coordinate_map
