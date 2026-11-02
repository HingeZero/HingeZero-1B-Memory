import json
from http.client import HTTPConnection
from hzdesktop.api import LocalAPI
from hzdesktop.vault import Vault


def request(port, path, body, token=None):
    c = HTTPConnection('127.0.0.1', port, timeout=3)
    headers = {'Content-Type':'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    c.request('POST', path, json.dumps(body), headers)
    response = c.getresponse()
    content = json.loads(response.read())
    status = response.status
    c.close()
    return status, content


def test_authorization_local_and_memory(tmp_path):
    with Vault(tmp_path / 'vault.db', 'correct-horse-battery-staple', create=True) as vault:
        api = LocalAPI(vault)
        try:
            assert api.http.server_address[0] == '127.0.0.1'
            assert request(api.port, '/v1/search', {'query':'hello'})[0] == 401
            assert request(api.port, '/v1/remember', {'title':'Project', 'content':'HingeZero remembers the project'}, api.token)[0] == 201
            status, data = request(api.port, '/v1/search', {'query':'HingeZero project'}, api.token)
            assert status == 200 and data['results'][0]['title'] == 'Project'
            assert request(api.port, '/v1/search', {'query':'hi'}, 'incorrect')[0] == 401
        finally:
            api.stop()


def test_read_only_token_searches_but_cannot_write(tmp_path):
    with Vault(tmp_path / "vault.db", "correct-horse-battery-staple", create=True) as vault:
        vault.add("Meeting", "Project milestone tomorrow")
        api = LocalAPI(vault)
        try:
            assert api.read_token != api.token
            status, data = request(api.port, "/v1/search",
                                   {"query": "project milestone"}, api.read_token)
            assert status == 200 and data["results"][0]["title"] == "Meeting"
            status, data = request(api.port, "/v1/remember",
                                   {"title": "unauthorised", "content": "new record"},
                                   api.read_token)
            assert status == 403
            assert len(vault.list()) == 1
            assert request(api.port, "/v1/search", {"query": "project"}, "invalid")[0] == 401
        finally:
            api.stop()
