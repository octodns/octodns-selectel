from requests import Session

from octodns import __VERSION__ as octodns_version

from .exceptions import ApiException


class DNSClient:
    API_URL = 'https://api.selectel.ru/domains/v2'
    _PAGINATION_LIMIT = 50

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
    def _rrset_path(cls, zone_uuid):
        return cls.__rrsets_path.format(zone_uuid)

    @classmethod
    def _rrset_path_specific(cls, zone_uuid, rrset_uuid):
        return cls.__rrsets_path_specific.format(zone_uuid, rrset_uuid)

    def _request(self, method, path, params=None, data=None):
        url = f'{self.API_URL}{path}'
        resp = self._sess.request(method, url, params, json=data)
        try:
            resp_json = resp.json()
        except ValueError:
            resp_json = {}
        match resp.status_code:
            case 200 | 201 | 204:
                return resp_json
            case 400 | 422:
                raise ApiException(
                    f'Bad request. Description: {resp_json.get("description", "Invalid payload")}.'
                )
            case 401:
                raise ApiException(
                    'Authorization failed. Invalid or empty token.'
                )
            case 404:
                raise ApiException(
                    'Resource not found: '
                    f'{resp_json.get("error", "invalid path")}.'
                )
            case 409:
                raise ApiException(
                    f'Conflict: {resp_json.get("error", "resource maybe already created")}.'
                )
            case _:
                raise ApiException('Internal server error.')

    def _request_all_entities(self, path, offset=0) -> list[int]:
        items = []
        resp = self._request(
            "GET", path, dict(limit=self._PAGINATION_LIMIT, offset=offset)
        )
        items.extend(resp["result"])
        if next_offset := resp["next_offset"]:
            items.extend(self._request_all_entities(path, offset=next_offset))
        return items

    def list_zones(self):
        return self._request_all_entities(self._zone_path)

    def create_zone(self, name):
        return self._request('POST', self._zone_path, data=dict(name=name))

    def list_rrsets(self, zone_uuid):
        path = self._rrset_path(zone_uuid)
        return self._request_all_entities(path)

    def create_rrset(self, zone_uuid, data):
        path = self._rrset_path(zone_uuid)
        return self._request('POST', path, data=data)

    def update_rrset(self, zone_uuid, rrset_uuid, data):
        path = self._rrset_path_specific(zone_uuid, rrset_uuid)
        return self._request('PATCH', path, data=data)

    def delete_rrset(self, zone_uuid, rrset_uuid):
        path = self._rrset_path_specific(zone_uuid, rrset_uuid)
        return self._request('DELETE', path)
