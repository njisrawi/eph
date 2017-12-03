import datetime
import os

import pytest

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

from eph import *
from eph.horizons import *
from eph.parsers import parse
from eph.exceptions import JplParserError, JplBadReqError


@pytest.fixture
def urls_file(res_dir):
    return os.path.join(res_dir, 'urls.txt')


@pytest.fixture
def urls(urls_file):
    with open(urls_file, 'r') as f:
        return f.readlines()


@pytest.fixture
def jpleph_file(res_dir):
    return os.path.join(res_dir, 'jpleph.txt')


@pytest.fixture
def jpleph(jpleph_file):
    with open(jpleph_file, 'r') as f:
        return f.read()


@pytest.fixture
def query():
    return {
        'COMMAND': '299',
        'START_TIME': '2000-1-1',
        'STOP_TIME': datetime.date.today().strftime('%Y-%m-%d'),
        'STEP': '2',
    }


@pytest.fixture
def jplreq(query):
    return JplReq(query)


@pytest.fixture(params=[
    (('target', 'earth'), ('COMMAND', '399')),
    (('Command', 'Earth'), ('COMMAND', '399')),
    (('OBJECT', '399'), ('COMMAND', '399')),
    (('Origin', 'earth'), ('CENTER', '@399')),
    (('bla', 'bla'), (None, None)),
])
def req_data(request):
    return request.param


def test_req(req_data):
    data, result = req_data
    key, value = data
    expected_key, expected_value = result
    try:
        req = JplReq({key: value})
        assert req[key] == expected_value
        assert getattr(req, key) == expected_value
        assert req[expected_key] == expected_value
        assert getattr(req, expected_key) == expected_value
    except Exception as e:
        assert e.__class__ == JplBadParamError


def test_url():
    req = JplReq({'COMMAND': '399'})
    assert req.url() == JPL_ENDPOINT + '&COMMAND=' + quote('\'399\'')


def test_query(config_file, jplreq):
    jplreq.read(config_file)
    res = jplreq.query().http_response
    assert res.status_code == 200


def test_get(urls):
    for url in urls:
        try:
            res = JplRes(requests.get(url))
            eph = res.raw()
            assert bool(eph)
        except JplBadReqError:
            assert False


def test_parse(jpleph):
    try:
        eph = parse(jpleph)
        assert bool(eph)
    except JplParserError:
        assert False
