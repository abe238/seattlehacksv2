from .luma import LumaParser
from .meetup import MeetupParser
from .eventbrite import EventbriteParser
from .generic import GenericParser

PARSERS = {
    "luma": LumaParser,
    "meetup": MeetupParser,
    "eventbrite": EventbriteParser,
    "generic": GenericParser,
}

def get_parser(source_type: str):
    return PARSERS.get(source_type, GenericParser)
