"""Contains classes and functions useful to interact with the `Jpl Horizons service`_ from NASA.

.. _`Jpl Horizons service`: https://ssd.jpl.nasa.gov/?horizons

"""


try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import requests

from .models import BaseMap
from .parsers import parse
from .exceptions import *
from ..config import read_config
from ..util import addparams2url, quote, yes_or_no


JPL_ENDPOINT = 'http://ssd.jpl.nasa.gov/horizons_batch.cgi?batch=1'

NAME2ID = dict(
    sun=10,
    mercury=199,
    venus=299,
    earth=399,
    mars=499,
    jupiter=599,
    saturn=699,
    uranus=799,
    neptune=899,
)

ID2NAME = {v: k for k, v in NAME2ID.items()}


def codify_obj(name):
    """Tries to translate a human readable celestial object name to the corresponding Jpl Horizons code.

    If the name is not known the name itself will be returned.

    Args:
         name (str): the name to be translated.

    Returns:
        str: the code of the object (stringified version of the id).

    """
    cleaned = name.strip('\'"')
    lowered = cleaned.lower()
    if lowered in NAME2ID.keys():
        id = NAME2ID[lowered]
        return str(id)
    else:
        return cleaned


def codify_site(name):
    """Tries to translate a human readable celestial object name to the corresponding Jpl Horizons site code.
    If the name is not known the name itself will be returned preceded by a @ sign
    if @ is not already present in the name.

    Args:
         name (str): the name to be translated.

    Returns:
        str: the code of the site.

    """
    cleaned = name.strip('\'"')
    lowered = cleaned.lower()
    if lowered in NAME2ID.keys():
        id = NAME2ID[lowered]
        return '@' + str(id)
    elif '@' in cleaned:
        return cleaned
    else:
        return '@' + cleaned


def humanify(code):
    """Tries to interpret a Jpl object or site code as a human readable celestial object name.

    Args:
        code (str): the code to be translated.

    Returns:
        str: the corresponding human readable name.

    """
    if code.isdigit():
        id = int(code)
    elif code.startswith('@') and code[1:].isdigit():
        id = int(code[1:])
    else:
        return code
    return ID2NAME.get(id, code)


JPL_PARAMS = {
    'COMMAND',
    'START_TIME',
    'STOP_TIME',
    'STEP_SIZE',
    'REF_PLANE',
    'REF_SYSTEM',
    'CENTER',
    'MAKE_EPHEM',
    'TABLE_TYPE',
    'VEC_TABLE',
    'OUT_UNITS',
    'CSV_FORMAT',
    'VEC_LABELS',
    'OBJ_DATA',
}

ALIASES = dict(
    COMMAND={'OBJECT', 'OBJ', 'BODY', 'TARGET'},
    START_TIME={'START', 'BEGIN', 'FROM'},
    STOP_TIME={'STOP', 'END', 'TO'},
    STEP_SIZE={'STEP', 'STEPS'},
    CENTER={'ORIGIN'},
    CSV_FORMAT={'CSV'},
    TABLE_TYPE={'TYPE'},
    VEC_TABLE={'TABLE'},
)


FILTERS = {
    codify_obj: ['COMMAND'],
    codify_site: ['CENTER'],
    yes_or_no: ['CSV_FORMAT'],
}


def transform_key(key):
    if key.upper() in JPL_PARAMS:
        return key.upper()
    for jplparam, aliases in ALIASES.items():
        if key.upper() in aliases:
            return jplparam


def transform_value(key, value):
    for filter, jplparams in FILTERS.items():
        if key in jplparams:
            return filter(value)
    return value


def transform(key, value):
    k = transform_key(key)
    v = transform_value(k, value)
    return k, v


class JplReq(BaseMap):
    """A requests to Jpl Horizons service.

    It can be thought as a :class:`dict` where key-value pairs represents Jpl Horizons parameters.
    Jpl parameters can be also set as attributes of the :class:`JplReq` instance.
    Furthermore, keys and values are adjusted to match Jpl Horizons interface in order to enhance
    readability and usability.

    """

    def __getattr__(self, key):
        key = transform_key(key)
        return super().__getattr__(key)

    def __setattr__(self, key, value):
        k, v = transform(key, value)
        if not k:
            raise JplBadParam('\'{}\' cannot be interpreted as a Jpl Horizons parameter.'.format(key))
        super().__setattr__(k, v)

    def __delattr__(self, key):
        key = transform_key(key)
        super().__delattr__(key)

    def read(self, filename, section='jplparams'):
        """Reads configurations parameters from an ini file.

        Reads the `section` section of the ini config file `filename` and set all parameters
        for the Jpl request.

        Args:
            filename (str): the config file to be read.
            section (str): the section of the ini config file to be read.

        Returns:
            :class:`JplReq`: the object itself.

        """
        cp = read_config(filename)
        jplparams = dict(cp.items(section))
        return self.set(jplparams)

    def url(self):
        """Calculate the Jpl Horizons url corresponding to the :class:`JplReq` object.

        Returns:
            str: the url with the Jpl parameters encoded in the query string.

        """
        return addparams2url(JPL_ENDPOINT, self)

    def query(self):
        """Performs the query to the Jpl Horizons service.

        Returns:
            :class:`JplRes`: the response from Jpl Horizons service.

        Raises:
            :class:`JplBadReq`

        """
        try:
            http_response = requests.get(JPL_ENDPOINT, params=self)
        except:
            raise ConnectionError
        if http_response.status_code == 200:
            return JplRes(http_response)
        else:
            raise JplBadReq


class JplRes(object):
    """A response from the Jpl Horizons service.

    """

    def __init__(self, http_response):
        """Initialize a :class:`JplRes` object from a `requests`_ http response object.

        Args:
            http_response: the http response from Jpl Horizons service.

        .. _`requests`: http://docs.python-requests.org/en/master/

        """
        self.http_response = http_response

    def get_raw(self):
        """Returns the content of the Jpl Horizons http response as is.

        """
        return self.http_response.text

    def get_table(self):
        """Parse the http response from Jpl Horizons and return an `astropy.table`_ object.

        .. _`astropy.table`: http://docs.astropy.org/en/stable/table/

        """
        return parse(self.get_raw())
