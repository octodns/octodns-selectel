from requests import Session

from octodns import __version__ as octodns_version

from .exceptions import ApiException


class DNSClient:
    API_URL = 'https://api.selectel.ru/domains/v2'
    _PAGINATION_LIMIT = 1000

    _zone_path = "/zones"
    __rrsets_path = "/zones/{}/rrset"
    __rrsets_path_specific = "/zones/{}/rrset/{}"

    def __init__(self, library_version: str, openstack_token: str):
        self._sess = Session()
        self._sess.headers.update(
            {
                'X-Auth-Token': openstack_token,
                'Content-Type': 'application/json',
                'User-Agent': f'octodns/{octodns_version} octodns-selectel/{library_version}',
            }
        )

    @classmethod
    def _rrset_path(cls, zone_id):
        return cls.__rrsets_path.format(zone_id)

    @classmethod
    def _rrset_path_specific(cls, zone_id, rrset_id):
        return cls.__rrsets_path_specific.format(zone_id, rrset_id)

    def _request(self, method, path, params=None, data=None):
        url = f'{self.API_URL}{path}'
        resp = self._sess.request(method, url, params, json=data)
        try:
            resp_json = resp.json()
        except ValueError:
            resp_json = {}
        if resp.status_code in {200, 201, 204}:
            return resp_json
        elif resp.status_code in {400, 422}:
            raise ApiException(
                f'Bad request. Description: {resp_json.get("description", "Invalid payload")}.'
            )
        elif resp.status_code == 401:
            raise ApiException('Authorization failed. Invalid or empty token.')
        elif resp.status_code == 404:
            raise ApiException(
                'Resource not found: '
                f'{resp_json.get("error", "invalid path")}.'
            )
        elif resp.status_code == 409:
            raise ApiException(
                f'Conflict: {resp_json.get("error", "resource maybe already created")}.'
            )
        else:
            raise ApiException('Internal server error.')

    def _request_all_entities(self, path, offset=0):
        items = []
        resp = self._request(
            "GET",
            path,
            dict(
                limit=self._PAGINATION_LIMIT,
                offset=offset,
                sort_by="name.descend",
            ),
        )
        items.extend(resp["result"])
        if next_offset := resp["next_offset"]:
            items.extend(self._request_all_entities(path, offset=next_offset))
        return items

    def list_zones(self):
        return self._request_all_entities(self._zone_path)

    def create_zone(self, name):
        return self._request('POST', self._zone_path, data=dict(name=name))

    def list_rrsets(self, zone_id):
        path = self._rrset_path(zone_id)
        return self._request_all_entities(path)

    def create_rrset(self, zone_id, data):
        path = self._rrset_path(zone_id)
        return self._request('POST', path, data=data)

    def update_rrset(self, zone_id, rrset_id, data):
        path = self._rrset_path_specific(zone_id, rrset_id)
        return self._request('PATCH', path, data=data)

    def delete_rrset(self, zone_id, rrset_id):
        path = self._rrset_path_specific(zone_id, rrset_id)
        return self._request('DELETE', path)
