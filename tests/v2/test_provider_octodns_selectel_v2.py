import uuid
from unittest import TestCase

import requests_mock

from octodns.record import Record, Update
from octodns.zone import Zone

from octodns_selectel.v2.dns_client import DNSClient
from octodns_selectel.v2.mappings import to_octodns_record_data
from octodns_selectel.v2.provider import SelectelProvider


class TestSelectelProvider(TestCase):
    _zone_id = str(uuid.uuid4())
    _zone_name = 'unit.tests.'
    _ttl = 3600
    rrsets = []
    octodns_zone = Zone(_zone_name, [])
    expected_records = set()
    selectel_zones = [dict(id=_zone_id, name=_zone_name)]
    _version = '0.0.1'
    _openstack_token = 'some-openstack-token'

    def _a_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='A',
            ttl=self._ttl,
            records=[dict(content='1.2.3.4'), dict(content='5.6.7.8')],
        )

    def _aaaa_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='AAAA',
            ttl=self._ttl,
            records=[
                dict(content="4ad4:a6c4:f856:18be:5a5f:7f16:cc3a:fab9"),
                dict(content="da78:f69b:8e5a:6221:d0c9:64b8:c6c0:2eab"),
            ],
        )

    def _cname_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='CNAME',
            ttl=self._ttl,
            records=[dict(content=self._zone_name)],
        )

    def _mx_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='MX',
            ttl=self._ttl,
            records=[dict(content=f'10 mx.{self._zone_name}')],
        )

    def _ns_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='NS',
            ttl=self._ttl,
            records=[
                dict(content=f'ns1.{self._zone_name}'),
                dict(content=f'ns2.{self._zone_name}'),
                dict(content=f'ns3.{self._zone_name}'),
            ],
        )

    def _srv_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='SRV',
            ttl=self._ttl,
            records=[
                dict(content=f'40 50 5050 foo-1.{self._zone_name}'),
                dict(content=f'50 60 6060 foo-2.{self._zone_name}'),
            ],
        )

    def _txt_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='TXT',
            ttl=self._ttl,
            records=[dict(content='"Foo1"'), dict(content='"Foo2"')],
        )

    def _sshfp_rrset(self, id, hostname):
        return dict(
            id=id,
            name=(
                f'{hostname}.{self._zone_name}' if hostname else self._zone_name
            ),
            type='SSHFP',
            ttl=self._ttl,
            records=[dict(content='1 1 123456789abcdef')],
        )

    def setUp(self):
        # A, subdomain=''
        a_id = str(uuid.uuid4())
        self.rrsets.append(self._a_rrset(a_id, ''))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                '',
                data=to_octodns_record_data(self._a_rrset(a_id, '')),
            )
        )
        # A, subdomain='sub'
        a_sub_id = str(uuid.uuid4())
        self.rrsets.append(self._a_rrset(a_sub_id, 'sub'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'sub',
                data=to_octodns_record_data(self._a_rrset(a_sub_id, 'sub')),
            )
        )

        # CNAME, subdomain='www2'
        cname_id = str(uuid.uuid4())
        self.rrsets.append(self._cname_rrset(cname_id, 'www2'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'www2',
                data=to_octodns_record_data(
                    self._cname_rrset(cname_id, 'www2')
                ),
            )
        )
        # CNAME, subdomain='wwwdot'
        cname_sub_id = str(uuid.uuid4())
        self.rrsets.append(self._cname_rrset(cname_sub_id, 'wwwdot'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'wwwdot',
                data=to_octodns_record_data(
                    self._cname_rrset(cname_sub_id, 'wwwdot')
                ),
            )
        )
        # MX, subdomain=''
        mx_id = str(uuid.uuid4())
        self.rrsets.append(self._mx_rrset(mx_id, ''))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                '',
                data=to_octodns_record_data(self._mx_rrset(mx_id, '')),
            )
        )
        # NS, subdomain='www3'
        ns_sub_id = str(uuid.uuid4())
        self.rrsets.append(self._ns_rrset(ns_sub_id, 'www3'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'www3',
                data=to_octodns_record_data(self._ns_rrset(ns_sub_id, 'www3')),
            )
        )
        # AAAA, subdomain=''
        aaaa_id = str(uuid.uuid4())
        self.rrsets.append(self._aaaa_rrset(aaaa_id, ''))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                '',
                data=to_octodns_record_data(self._aaaa_rrset(aaaa_id, '')),
            )
        )
        # SRV, subdomain='_srv._tcp'
        srv_id = str(uuid.uuid4())
        self.rrsets.append(self._srv_rrset(srv_id, '_srv._tcp'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                '_srv._tcp',
                data=to_octodns_record_data(
                    self._srv_rrset(srv_id, '_srv._tcp')
                ),
            )
        )
        # TXT, subdomain='txt'
        txt_id = str(uuid.uuid4())
        self.rrsets.append(self._txt_rrset(txt_id, 'txt'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'txt',
                data=to_octodns_record_data(self._txt_rrset(txt_id, 'txt')),
            )
        )
        # SSHFP, subdomain='sshfp'
        sshfp_id = str(uuid.uuid4())
        self.rrsets.append(self._sshfp_rrset(sshfp_id, 'sshfp'))
        self.expected_records.add(
            Record.new(
                self.octodns_zone,
                'sshfp',
                data=to_octodns_record_data(
                    self._sshfp_rrset(sshfp_id, 'sshfp')
                ),
            )
        )

    def tearDown(self):
        self.rrsets.clear()
        self.expected_records.clear()
        self.octodns_zone = Zone(self._zone_name, [])

    @requests_mock.Mocker()
    def test_populate(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=self.rrsets, limit=len(self.rrsets), next_offset=0
            ),
        )
        zone = Zone(self._zone_name, [])

        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)

        self.assertEqual(len(self.rrsets), len(zone.records))
        self.assertEqual(self.expected_records, zone.records)

    @requests_mock.Mocker()
    def test_apply(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(result=list(), limit=0, next_offset=0),
        )
        fake_http.post(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/rrset', json=dict()
        )

        provider = SelectelProvider(
            self._version, self._openstack_token, strict_supports=False
        )

        zone = Zone(self._zone_name, [])
        for record in self.expected_records:
            zone.add_record(record)

        plan = provider.plan(zone)
        self.assertEqual(len(self.expected_records), len(plan.changes))
        self.assertEqual(len(self.expected_records), provider.apply(plan))

    @requests_mock.Mocker()
    def test_apply_with_create_zone(self, fake_http):
        zone_name_for_created = 'octodns-zone.test.'
        zone_id = "bdd902e7-7270-44c8-8d18-120fa5e1e5d4"
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(result=list(), limit=0, next_offset=0),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(result=list(), limit=0, next_offset=0),
        )
        fake_http.post(
            f'{DNSClient.API_URL}/zones',
            json=dict(id=zone_id, name=zone_name_for_created),
        )
        fake_http.post(f'{DNSClient.API_URL}/zones/{zone_id}/rrset')
        zone = Zone(zone_name_for_created, [])
        provider = SelectelProvider(
            self._version, self._openstack_token, strict_supports=False
        )
        provider.populate(zone)

        zone.add_record(
            Record.new(
                zone, '', data=dict(ttl=self._ttl, type="A", values=["1.2.3.4"])
            )
        )

        plan = provider.plan(zone)
        apply_len = provider.apply(plan)
        self.assertEqual(1, apply_len)

    @requests_mock.Mocker()
    def test_populate_with_not_supporting_type(self, fake_http):
        rrsets_with_not_supporting_type = self.rrsets
        rrsets_with_not_supporting_type.append(
            dict(
                name=self._zone_name,
                ttl=self._ttl,
                type="SOA",
                records=[
                    dict(
                        content="a.ns.selectel.ru. support.selectel.ru. "
                        "2023122202 10800 3600 604800 60"
                    )
                ],
            )
        )

        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=rrsets_with_not_supporting_type,
                limit=len(self.rrsets),
                next_offset=0,
            ),
        )

        zone = Zone(self._zone_name, [])
        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)

        self.assertNotEqual(
            len(rrsets_with_not_supporting_type), len(zone.records)
        )
        self.assertNotEqual(rrsets_with_not_supporting_type, zone.records)

    @requests_mock.Mocker()
    def test_apply_update_ttl(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )

        updated_rrset = self.rrsets[0]
        updated_record = Record.new(
            zone=self.octodns_zone,
            name=self.octodns_zone.hostname_from_fqdn(updated_rrset["name"]),
            data=to_octodns_record_data(updated_rrset),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=[self._a_rrset(updated_rrset["id"], '')],
                limit=len(self.rrsets),
                next_offset=0,
            ),
        )

        updated_rrset["ttl"] *= 2
        fake_http.patch(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/rrset/{updated_rrset["id"]}',
            status_code=204,
        )

        zone = Zone(self._zone_name, [])
        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)

        zone.remove_record(updated_record)
        updated_record.ttl *= 2
        zone.add_record(updated_record)

        plan = provider.plan(zone)
        apply_len = provider.apply(plan)

        self.assertEqual(1, apply_len)

    @requests_mock.Mocker()
    def test_apply_update_ttl_internal_error(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )

        updated_rrset = self.rrsets[0]
        updated_record = Record.new(
            zone=self.octodns_zone,
            name=self.octodns_zone.hostname_from_fqdn(updated_rrset["name"]),
            data=to_octodns_record_data(updated_rrset),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=[self._a_rrset(updated_rrset["id"], '')],
                limit=len(self.rrsets),
                next_offset=0,
            ),
        )

        updated_rrset["ttl"] *= 2
        fake_http.patch(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/rrset/{updated_rrset["id"]}',
            status_code=500,
        )

        zone = Zone(self._zone_name, [])
        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)

        zone.remove_record(updated_record)
        updated_record.ttl *= 2
        zone.add_record(updated_record)

        plan = provider.plan(zone)

        with self.assertLogs(provider.log, "WARNING"):
            apply_len = provider.apply(plan)
            self.assertEqual(1, apply_len)

    @requests_mock.Mocker()
    def test_apply_delete(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        deleted_rrset = self.rrsets[0]
        deleted_record = Record.new(
            zone=self.octodns_zone,
            name=self.octodns_zone.hostname_from_fqdn(deleted_rrset["name"]),
            data=to_octodns_record_data(deleted_rrset),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=[self._a_rrset(deleted_rrset["id"], '')],
                limit=len(self.rrsets),
                next_offset=0,
            ),
        )

        fake_http.delete(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/rrset/{deleted_rrset["id"]}'
        )

        zone = Zone(self._zone_name, [])
        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)

        zone.remove_record(deleted_record)

        plan = provider.plan(zone)
        apply_len = provider.apply(plan)

        self.assertEqual(1, apply_len)

    @requests_mock.Mocker()
    def test_apply_delete_with_error(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        fake_http.get(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/'
            f'rrset?limit={DNSClient._PAGINATION_LIMIT}&offset=0',
            json=dict(
                result=self.rrsets, limit=len(self.rrsets), next_offset=0
            ),
        )
        deleted_rrset = self.rrsets[0]
        deleted_record = Record.new(
            zone=self.octodns_zone,
            name=self.octodns_zone.hostname_from_fqdn(deleted_rrset["name"]),
            data=to_octodns_record_data(deleted_rrset),
        )

        fake_http.delete(
            f'{DNSClient.API_URL}/zones/{self._zone_id}/rrset/{deleted_rrset["id"]}',
            status_code=500,
        )

        zone = Zone(self._zone_name, [])
        provider = SelectelProvider(self._version, self._openstack_token)
        provider.populate(zone)
        zone.remove_record(deleted_record)

        plan = provider.plan(zone)

        with self.assertLogs(provider.log, "WARNING"):
            apply_len = provider.apply(plan)
            self.assertEqual(1, apply_len)

    @requests_mock.Mocker()
    def test_include_change_returns_false(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )

        provider = SelectelProvider(self._version, self._openstack_token)
        zone = Zone(self._zone_name, [])

        exist_record = Record.new(
            zone, '', dict(ttl=60, type="A", values=["1.2.3.4"])
        )
        change = Update(exist_record, exist_record)
        include_change = provider._include_change(change)

        self.assertFalse(include_change)

    @requests_mock.Mocker()
    def test_include_change_sshfp_returns_false(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )

        provider = SelectelProvider(self._version, self._openstack_token)
        zone = Zone(self._zone_name, [])
        fingerprint1 = '123456789abcdef'
        fingerprint2 = 'abcdef123456789'
        exist_record = Record.new(
            zone,
            '',
            dict(
                ttl=60,
                type="SSHFP",
                values=[
                    dict(
                        algorithm=1,
                        fingerprint_type=1,
                        fingerprint=fingerprint1,
                    ),
                    dict(
                        algorithm=1,
                        fingerprint_type=1,
                        fingerprint=fingerprint2,
                    ),
                ],
            ),
        )
        new_record = Record.new(
            zone,
            '',
            dict(
                ttl=60,
                type="SSHFP",
                values=[
                    dict(
                        algorithm=1,
                        fingerprint_type=1,
                        fingerprint=fingerprint1.upper(),
                    ),
                    dict(
                        algorithm=1,
                        fingerprint_type=1,
                        fingerprint=fingerprint2.upper(),
                    ),
                ],
            ),
        )
        change = Update(exist_record, new_record)
        include_change = provider._include_change(change)

        self.assertFalse(include_change)

    @requests_mock.Mocker()
    def test_include_change_returns_true(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )

        provider = SelectelProvider(self._version, self._openstack_token)
        zone = Zone(self._zone_name, [])

        exist_record = Record.new(
            zone, '', dict(ttl=60, type="A", values=["1.2.3.4"])
        )
        new = Record.new(zone, '', dict(ttl=70, type="A", values=["1.2.3.4"]))
        change = Update(exist_record, new)
        include_change = provider._include_change(change)

        self.assertTrue(include_change)

    @requests_mock.Mocker()
    def test_list_zones(self, fake_http):
        fake_http.get(
            f'{DNSClient.API_URL}/zones',
            json=dict(
                result=self.selectel_zones,
                limit=len(self.selectel_zones),
                next_offset=0,
            ),
        )
        provider = SelectelProvider(self._version, self._openstack_token)
        zones = provider.list_zones()

        self.assertListEqual(zones, self._zone_name.split())
