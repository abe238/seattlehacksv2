from .luma import LumaParser
from .meetup import MeetupParser
from .eventbrite import EventbriteParser
from .generic import GenericParser
from .tentimes import TenTimesParser

PARSERS = {
    "luma": LumaParser,
    "meetup": MeetupParser,
    "eventbrite": EventbriteParser,
    "generic": GenericParser,
    "tentimes": TenTimesParser,
}

def get_parser(source_type: str):
    return PARSERS.get(source_type, GenericParser)
