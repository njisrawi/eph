"""Contains classes and functions useful to interact with the `Jpl Horizons service`_ from NASA.

.. _`Jpl Horizons service`: https://ssd.jpl.nasa.gov/?horizons

"""


import requests
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from .models import BaseMap
from .interface import JPL_ENDPOINT, transform_key, transform
from .exceptions import JplBadParam
from .parsers import parse, get_sections
from ..config import read_config
from ..eph import Eph
from ..util import addparams2url



class JplReq(BaseMap):
    """A requests to Jpl Horizons service.

    It can be thought as a :class:`dict` where key-value pairs represents Jpl Horizons parameters.
    Jpl parameters can be also set as attributes of the :class:`JplReq` instance.
    Furthermore, keys and values are adjusted to match Jpl Horizons interface in order to enhance
    readability and usability.

    """

    def __getattr__(self, key):
        key = transform_key(key)
        return super(self.__class__, self).__getattr__(key)

    def __setattr__(self, key, value):
        k, v = transform(key, value)
        if not k:
            raise JplBadParam('\'{0}\' cannot be interpreted as a Jpl Horizons parameter'.format(key))
        super(self.__class__, self).__setattr__(k, v)

    def __delattr__(self, key):
        key = transform_key(key)
        super(self.__class__, self).__delattr__(key)

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
            :class:`ConnectionError`

        """

        try:
            http_response = requests.get(JPL_ENDPOINT, params=self)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(e.__str__())

        return JplRes(http_response)


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

    def get_header(self):
        header, ephem, footer = get_sections(self.get_raw())
        return header

    def get_data(self):
        header, data, footer = get_sections(self.get_raw())
        return data

    def get_footer(self):
        header, ephemeris, footer = get_sections(self.get_raw())
        return footer

    def parse(self, target=Eph):
        """Parse the http response from Jpl Horizons and return, according to target

         * an `astropy.table.Table`_ object.
         * an `astropy.table.QTable`_ object.
         * an `eph.Eph` object.

        .. _`astropy.table`: http://docs.astropy.org/en/stable/table/

        """
        return parse(self.get_raw(), target=target)

    def __str__(self):
        return self.get_raw()

