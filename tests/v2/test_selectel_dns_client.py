from unittest import TestCase

import requests_mock

from octodns_selectel.v2.dns_client import DNSClient
from octodns_selectel.v2.exceptions import ApiException


class TestSelectelDNSClient(TestCase):
    zone_name = "test-octodns.ru."
    zone_id = "01073035-cc25-4956-b0c9-b3a270091c37"
    rrset_id = "03073035-dd25-4956-b0c9-k91270091d95"
    project_id = "763219cb96c141978e8d45da637ae75c"
    library_version = "0.0.1"
    openstack_token = "some-openstack-token"
    dns_client = DNSClient(library_version, openstack_token)
    _PAGINATION_LIMIT = 50
    _PAGINATION_OFFSET = 0
    _rrsets = [
        dict(
            id="0eb2f04e-74fd-4264-a4b8-396e5fc95f00",
            name=zone_name,
            ttl=3600,
            type="SOA",
            records=[
                dict(
                    content="a.ns.selectel.ru. support.selectel.ru. 2023122202 10800 "
                    "3600 604800 60",
                    disabled=False,
                )
            ],
            zone_id=zone_id,
        ),
        dict(
            id="0eb2f04e-74fd-4264-a4b8-396e5fc95f00",
            name=zone_name,
            ttl=3600,
            type="NS",
            records=[
                dict(content="a.ns.selectel.ru.", disabled=False),
                dict(content="b.ns.selectel.ru.", disabled=False),
                dict(content="c.ns.selectel.ru.", disabled=False),
                dict(content="d.ns.selectel.ru.", disabled=False),
            ],
            zone_id=zone_id,
        ),
    ]
    _response_list_rrset_without_offset = dict(
        count=2, next_offset=0, result=_rrsets
    )
    _response_list_rrset_with_offset = dict(
        count=2, next_offset=2, result=_rrsets
    )

    @requests_mock.Mocker()
    def test_request_unauthorized_with_html_body(self, fake_http):
        response_unauthorized_html = """
            <html>
            <head><title>401 Authorization Required</title></head>
            <body>
                <center><h1>401 Authorization Required</h1></center>
                <hr><center>nginx</center>
            </body>
            </html>
        """
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            status_code=401,
            headers={"X-Auth-Token": self.openstack_token},
            text=response_unauthorized_html,
        )
        with self.assertRaises(ApiException) as api_exception:
            self.dns_client.list_zones()
        self.assertEqual(
            'Authorization failed. Invalid or empty token.',
            str(api_exception.exception),
        )

    @requests_mock.Mocker()
    def test_request_bad_request_with_description(self, fake_http):
        bad_response = dict(error="bad_request", description=("field required"))
        fake_http.post(
            f'{DNSClient.API_URL}/zones',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=422,
            json=bad_response,
        )
        with self.assertRaises(ApiException) as api_exception:
            self.dns_client.create_zone(self.zone_name)
        self.assertEqual(
            f'Bad request. Description: {bad_response.get("description")}.',
            str(api_exception.exception),
        )

    @requests_mock.Mocker()
    def test_request_resource_not_found(self, fake_http):
        bad_response_with_resource_not_found = dict(
            error="zone_not_found", description="invalid value"
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=404,
            json=bad_response_with_resource_not_found,
        )
        with self.assertRaises(ApiException) as api_exception:
            self.dns_client.list_rrsets(self.zone_id)
        self.assertEqual(
            f'Resource not found: {bad_response_with_resource_not_found["error"]}.',
            str(api_exception.exception),
        )

    @requests_mock.Mocker()
    def test_request_resource_conflict(self, fake_http):
        bad_response_with_resource_not_found = dict(
            error="this_rrset_is_already_exists", description="invalid value"
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=409,
            json=bad_response_with_resource_not_found,
        )
        with self.assertRaises(ApiException) as api_exception:
            self.dns_client.list_rrsets(self.zone_id)
        self.assertEqual(
            f'Conflict: {bad_response_with_resource_not_found["error"]}.',
            str(api_exception.exception),
        )

    @requests_mock.Mocker()
    def test_request_internal_error(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=500,
            json={},
        )
        with self.assertRaises(ApiException) as api_exception:
            self.dns_client.list_zones()
        self.assertEqual('Internal server error.', str(api_exception.exception))

    @requests_mock.Mocker()
    def test_request_all_entities_without_offset(self, fake_http):
        response_without_offset = self._response_list_rrset_without_offset
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=response_without_offset,
        )
        all_entities = self.dns_client._request_all_entities(
            DNSClient._rrset_path(self.zone_id)
        )
        self.assertEqual(response_without_offset["result"], all_entities)

    @requests_mock.Mocker()
    def test_request_all_entities_with_offset(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset?limit={self._PAGINATION_LIMIT}',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=self._response_list_rrset_with_offset,
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/'
            f'rrset?limit={self._PAGINATION_LIMIT}&offset=2',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=self._response_list_rrset_without_offset,
        )
        all_entities = self.dns_client._request_all_entities(
            DNSClient._rrset_path(self.zone_id)
        )
        result_list = []
        result_list.extend(self._rrsets)
        result_list.extend(self._rrsets)
        self.assertEqual(result_list, all_entities)

    @requests_mock.Mocker()
    def test_list_zone_success(self, fake_http):
        response_without_offset = dict(
            count=1,
            next_offset=0,
            result=[
                dict(
                    id="0eb2f07g-74fd-4271-a4b8-396e5fc95f60",
                    name=self.zone_name,
                    project_id=self.project_id,
                    created_at="2023-12-22T12:44:36Z",
                    updated_at="2023-12-22T13:34:14Z",
                    comment=None,
                    disabled=False,
                    delegation_checked_at="2023-12-22T13:34:14Z",
                    last_delegated_at=None,
                    last_check_status=False,
                )
            ],
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=response_without_offset,
        )
        zones = self.dns_client.list_zones()
        self.assertEqual(response_without_offset["result"], zones)

    @requests_mock.Mocker()
    def test_create_zone_success(self, fake_http):
        response_created_zone = dict(
            id="bdd902e7-7270-44c8-8d18-120fa5e1e5d4",
            name=self.zone_name,
            project_id=self.project_id,
            created_at="2023-12-22T15:07:31Z",
            updated_at="2023-12-22T15:07:31Z",
            comment=None,
            disabled=False,
            delegation_checked_at=None,
            last_delegated_at=None,
            last_check_status=False,
        )
        fake_http.post(
            f'{DNSClient.API_URL}/zones',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=response_created_zone,
        )
        zone = self.dns_client.create_zone(self.zone_name)
        self.assertEqual(response_created_zone, zone)

    @requests_mock.Mocker()
    def test_list_rrsets_success(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=self._response_list_rrset_without_offset,
        )
        rrsets = self.dns_client.list_rrsets(self.zone_id)
        self.assertEqual(
            self._response_list_rrset_without_offset["result"], rrsets
        )

    @requests_mock.Mocker()
    def test_create_rrset_success(self, fake_http):
        response_created_rrset = dict(
            id=self.rrset_id,
            name=self.zone_name,
            project_id=self.project_id,
            created_at="2023-12-22T15:07:31Z",
            updated_at="2023-12-22T15:07:31Z",
            comment=None,
            disabled=False,
            delegation_checked_at=None,
            last_delegated_at=None,
            last_check_status=False,
        )
        fake_http.post(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
            json=response_created_rrset,
        )
        rrsets = self.dns_client.create_rrset(self.zone_id, dict())
        self.assertEqual(response_created_rrset, rrsets)

    @requests_mock.Mocker()
    def test_delete_rrset_success(self, fake_http):
        fake_http.delete(
            f'{DNSClient.API_URL}/zones/{self.zone_id}/rrset/{self.rrset_id}',
            headers={"X-Auth-Token": self.openstack_token},
            status_code=200,
        )
        response_from_delete = self.dns_client.delete_rrset(
            self.zone_id, self.rrset_id
        )
        self.assertEqual(dict(), response_from_delete)
