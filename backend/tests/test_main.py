from fastapi.testclient import TestClient
from fastapi import FastAPI
from functools import lru_cache
import unittest.mock

from middleware import set_cors
from main import app, county_list
from tests.denver_county_data import cache, no_cache
from utils.config import Settings
from utils.helper import RedisHelper

client = TestClient(app)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings: Settings = get_settings()


def setup_function(function):
    """ setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """
    function.r = RedisHelper(settings.hostname, settings.port, settings.password)


def teardown_function(function):
    """ teardown any state that was previously setup with a setup_function
    call.
    """
    del function.r


def test_get_counties():
    response = client.get('/counties')
    assert response.status_code == 200
    assert response.json() == {"counties": county_list}


def test_get_county_data_no_cache():
    #response_json = json.dumps(response.__dict__)
    test_get_county_data_no_cache.r.reset_cache()
    returned_response = client.get('/counties/31')
    
    assert returned_response.status_code == 200
    assert returned_response.json() == no_cache


@unittest.mock.patch('utils.helper.RedisHelper.getCurrentTime')
def test_get_county_data_cache(mock_getCurrentTime):
    #Patch current time.  If the timing between two get_current_time falls at the end of a second this can randomly fail
    current_time = "13:37:00"
    mock_getCurrentTime.return_value = current_time
    cache["last_updated"] = current_time

    #Reset and pre-seed the cache
    test_get_county_data_cache.r.reset_cache()
    client.get('/counties/31')
    
    #Return cached response
    returned_response = client.get('/counties/31')

    assert mock_getCurrentTime.called
    assert mock_getCurrentTime.call_count == 1
    assert returned_response.status_code == 200
    assert returned_response.json() == cache


def test_get_county_data_county_error():
    returned_response = client.get('/counties/RANDOM COUNTY THAT DOES NOT EXIST')
    assert returned_response.status_code == 404
    assert returned_response.json() == {"detail": "County not found in database"}


def test_cors():
    # start the sever
    cors_app = FastAPI()

    # cors hasn't been set yet
    assert cors_app.user_middleware == []

    # set cors
    set_cors(cors_app)

    assert cors_app.user_middleware != []

    # For now, there is only one middleware set up, but this should work for multiple
    expected_mw_options: dict = {'allow_origins': ['*'], 'allow_credentials': True}
    mw_options = [m.options for m in cors_app.user_middleware if hasattr(m, 'options')]
    assert expected_mw_options in mw_options
