import os
import re
import warnings
from dataclasses import dataclass
from typing import List, Optional, Pattern, Set

import toml

from philter_lite.filters import filter_db


@dataclass(frozen=True)
class Filter:
    title: str
    type: str
    exclude: bool
    phi_type: str


@dataclass(frozen=True)
class SetFilter(Filter):
    pos: Set[str]
    data: Set[str]


@dataclass(frozen=True)
class RegexFilter(Filter):
    data: Pattern[str]


@dataclass(frozen=True)
class RegexContextFilter(Filter):
    context: str
    context_filter: str
    data: Pattern[str]


@dataclass(frozen=True)
class PosFilter(Filter):
    pos: List[str]


@dataclass(frozen=True)
class NerFilter(Filter):
    pos: Optional[List[str]]


_DAY_NAME = "(S|s)un(day)?(s)?|SUN(DAY)?(S)?|(M|m)on(day)?(s)?|MON(DAY)?(S)?|(T|t)ues(day)?(s)?|Tue|TUES(DAY)?(S)?|(W|w)ed(nesday)?(s)?|WED(NESDAY)?(S)?|(T|t)hurs(day)?(s)?|Thu|THURS(DAY)?(S)?|(F|f)ri(day)?(s)?|FRI(DAY)?(S)?|(S|s)at(urday)?(s)?|SAT(URDAY)?(S)?"
_MONTH_NAME = "(J|j)an(uary)?|JAN(UARY)?|(F|f)eb(ruary)?|FEB(RUARY)?|(M|m)ar(ch)?|MAR(CH)?|(A|a)pr(il)?|APR(IL)?|May|MAY|(J|j)un(e)?|JUN(E)?|(J|j)ul(y)?|JUL(Y)?|(A|a)ug(ust)?|AUG(UST)?|(S|s)ep(tember)?|SEP(TEMBER)?|SEPT|Sept|(O|o)ct(ober)?|OCT(OBER)?|(N|n)ov(ember)?|NOV(EMBER)?|(D|d)ec(ember)?|DEC(EMBER)?"
_DAY_NUMBERING = "1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th|13th|14th|15th|16th|17th|18th|19th|20th|21st|22nd|23rd|24th|25th|26th|27th|28th|29th|30th|31st|32nd|33rd|34th|35th|36th|37th|38th|39th|40th|41st|42nd|43rd|44th|45th|46th|47th|48th|49th|50th"
_SEASONS = "(S|s)pring|SPRING|(F|f)all|FALL|(A|a)utumn|AUTUMN|(W|w)inter|WINTER|(S|s)ummer|SUMMER|(C|c)hristmas|(N|n)ew (Y|y)ear's (E|e)ve"
_ADDRESS_INDICATOR = "alley|alley|ally|aly|anex|annex|annx|anx|apartment|apt|avenue|ave|aven|avenu|avenue|avn|avnue|bayou|bayou|beach|beach|bnd|bluff|bluf|bluff|bluffs|boulevard|boul|boulevard|blvd|boulv|box|branch|brnch|branch|bridge|brg|bridge|brook|brook|brooks|burg|burgs|byps|canyon|canyon|cnyn|cape|cpe|causeway|causwa|cswy|cent|centr|centre|cnter|cntr|ctr|circle|circ|circl|circle|crcl|crcle|circles|cliff|cliff|cliffs|cliffs|club|club|commons|corner|corner|corners|cors|crse|court|ct|courts|cts|cove|cv|coves|creek|crk|crescent|cres|crsent|crsnt|crest|crossing|crssng|xing|crossroad|crossroads|dale|dl|dam|divide|divide|dv|dvd|drive|driv|dr|drv|drives|east|estate|estate|estates|ests|expressway|expr|express|expressway|expw|expy|extn|extnsn|fls|ferry|frry|fry|flat|flt|flats|flts|ford|frd|fords|forest|forests|frst|forge|forge|frg|forges|fork|frk|forks|frks|fort|frt|ft|freeway|freewy|frway|frwy|fwy|garden|gardn|grden|grdn|gardens|gdns|grdns|gateway|gatewy|gatway|gtway|gtwy|glen|gln|glens|green|grn|greens|grove|grove|grv|groves|harbor|harbor|harbr|hbr|hrbor|harbors|haven|hvn|heights|hts|highway|highwy|hiway|hiwy|hway|hwy|hill|hl|hills|hls|hollow|hollow|hollows|holw|holws|iss|isle|isles|knoll|knol|knoll|knolls|knolls|lake|lake|lakes|lakes|land|landing|lndg|lndng|lane|ln|loaf|loaf|lock|lock|locks|locks|ldge|lodg|lodge|loop|loops|mall|manor|manor|manors|mnrs|meadow|meadows|mdws|meadows|medows|mews|mill|mills|mission|mssn|motorway|north|orchard|orchard|orchrd|oval|ovl|overpass|park|prk|parks|parkway|parkwy|pkway|pkwy|pky|parkways|pkwys|pass|passage|pike|pikes|pine|pines|pnes|place|plain|pln|plains|plns|plaza|plz|plza|port|prt|ports|prts|prairie|prairie|prr|ramp|ranch|ranches|rnch|rnchs|rapids|rpds|rst|ridge|rdge|ridge|ridges|ridges|river|river|rvr|rivr|road|road|rd|roads|rds|route|row|run|shoal|shoal|shoals|shoals|shore|shore|shr|shores|shores|shrs|skyway|south|spring|spng|spring|sprng|springs|spngs|springs|sprngs|spur|spurs|square|sqr|sqre|squ|square|squares|squares|station|station|statn|stn|stravenue|strav|straven|stravenue|stravn|strvn|strvnue|stream|streme|strm|street|strt|st|str|streets|suite|summit|sumit|sumitt|summit|terrace|terr|terrace|throughway|trce|track|tracks|trak|trk|trks|trafficway|trail|trails|trl|trls|trailer|trlr|trlrs|tunnel|tunl|tunls|tunnel|tunnels|tunnl|turnpike|turnpike|turnpk|underpass|union|union|unions|valley|vally|vlly|vly|valleys|vlys|viaduct|viadct|viaduct|village|villag|village|villg|villiage|vlg|villages|vlgs|ville|vl|vista|vist|vista|vst|vsta|way|way|ways|west|wls"
_STATE_NAMES = "(A|a)rizona|AZ|(V|v)irginia|VA|(M|m)innesota|MN|(A|a)laska|AK|(N|n)ew (Y|y)ork|NY|(T|t)exas|TX|(V|v)ermont|VT|(U|u)tah|UT|(N|n)ew (J|j)ersey|NJ|(N|n)orth (D|d)akota|ND|(S|s)outh (D|d)akota|SD|(M|m)issouri|MO|(W|w)ashington (D|d).(C|c).|(G|g)eorgia|GA|(M|m)assachusetts|MA|(P|p)uerto (R|r)ico|(M|m)ichigan|MI|(I|i)owa|IA|(N|n)orth (C|c)arolina|NC|(S|s)outh (C|c)arolina|SC|(N|n)evada|NV|(C|c)olorado|CO|(O|o)hio|OH|(H|h)awaii|HI|(N|n)ebraska|NE|(N|n)ew (H|h)ampshire|NH|(W|w)ashington|WA|(T|t)ennessee|TN|(A|a)rkansas|AR|(L|l)ouisiana|LA|(M|m)ississippi|MS|(O|o)regon|OR|(A|a)labama|AL|(W|w)yoming|WY|(W|w)isconsin|WI|(O|o)klahoma|OK|(F|f)lorida|FL|(R|r)hode (I|i)sland|RI|(I|i)ndiana|IN|(C|c)alifornia|CA|(K|k)ansas|KS|(D|d)elaware|DE|(M|m)aryland|(I|i)daho|ID|(P|p)ennsylvania|PA|(K|k)entucky|KY|(C|c)onnecticut|CT|(M|m)ontana|MT|(I|i)llinois|IL|(M|m)aine|ME"
_FULL_NUMBERING = "First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth"


def filter_from_dict(
    filter_dict,
    regex_db=filter_db.regex_db,
    regex_context_db=filter_db.regex_context_db,
    set_db=filter_db.set_db,
):
    known_pattern_types = {
        "regex",
        "set",
        "regex_context",
        "stanford_ner",
        "pos_matcher",
        "match_all",
    }

    filter_type = filter_dict["type"]

    if filter_type not in known_pattern_types:
        raise Exception("Pattern type is unknown", filter_type)

    if filter_type == "set":
        set_keyword = filter_dict["keyword"]
        data = _nested_get(set_db, set_keyword.split("."))
        return SetFilter(
            title=filter_dict["title"],
            type=filter_type,
            exclude=filter_dict["exclude"],
            data=set(data),
            pos=set(filter_dict["pos"]),
            phi_type=filter_dict.get("phi_type", "OTHER"),
        )
    elif filter_type == "regex":
        regex_keyword = filter_dict["keyword"]
        regex = _nested_get(regex_db, regex_keyword.split("."))
        regex = _interpolate_regex(regex)
        data = _precompile(regex)
        return RegexFilter(
            title=filter_dict["title"],
            type=filter_type,
            exclude=filter_dict["exclude"],
            data=data,
            phi_type=filter_dict.get("phi_type", "OTHER"),
        )

    elif filter_type == "regex_context":
        regex_keyword = filter_dict["keyword"]
        regex = _nested_get(regex_context_db, regex_keyword.split("."))
        data = _precompile(regex)

        return RegexContextFilter(
            title=filter_dict["title"],
            type=filter_type,
            exclude=filter_dict["exclude"],
            context=filter_dict["context"],
            context_filter=filter_dict["context_filter"],
            data=data,
            phi_type=filter_dict.get("phi_type", "OTHER"),
        )
    elif filter_type == "pos_matcher":
        return PosFilter(
            title=filter_dict["title"],
            type=filter_type,
            exclude=filter_dict["exclude"],
            pos=filter_dict["pos"],
            phi_type=filter_dict.get("phi_type", "OTHER"),
        )
    else:
        return Filter(
            title=filter_dict["title"],
            type=filter_type,
            exclude=filter_dict["exclude"],
            phi_type=filter_dict.get("phi_type", "OTHER"),
        )


def load_filters(filter_path) -> List[Filter]:
    """Loads filters from a file on disk.

    File must be a toml file with a key of `filters`
    """
    if not os.path.exists(filter_path):
        raise Exception("Filepath does not exist", filter_path)
    with open(filter_path, "r") as fil_file:
        return [filter_from_dict(x) for x in toml.loads(fil_file.read())["filters"]]


def _precompile(regex: str):
    """precompiles our regex to speed up pattern matching"""
    # NOTE: this is not thread safe! but we want to print a more detailed warning message
    with warnings.catch_warnings():
        warnings.simplefilter(
            action="error", category=FutureWarning
        )  # in order to print a detailed message
        try:
            re_compiled = re.compile(regex)
        except FutureWarning:
            warnings.simplefilter(action="ignore", category=FutureWarning)
            re_compiled = re.compile(regex)  # assign nevertheless
    return re_compiled


def _nested_get(a_dict, keys):
    for key in keys:
        a_dict = a_dict[key]
    return a_dict


def _interpolate_regex(regex_string: str):
    regex = (
        regex_string.replace('"""+month_name+r"""', _MONTH_NAME)
        .replace('"""+day_numbering+r"""', _DAY_NUMBERING)
        .replace('"""+day_name+r"""', _DAY_NAME)
        .replace('"""+seasons+r"""', _SEASONS)
        .replace('"""+address_indicator+r"""', _ADDRESS_INDICATOR)
        .replace('"""+state_name+r"""', _STATE_NAMES)
        .replace('"""+full_numbering+r"""', _FULL_NUMBERING)
    )
    return regex
