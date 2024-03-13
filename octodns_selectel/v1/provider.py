from collections import defaultdict
from logging import getLogger

from requests import Session
from requests.exceptions import HTTPError

from octodns import __version__ as octodns_version
from octodns.provider import ProviderException
from octodns.provider.base import BaseProvider
from octodns.record import Record, Update

from octodns_selectel.escaping_semicolon import (
    escape_semicolon,
    unescape_semicolon,
)
from octodns_selectel.version import __version__ as provider_version


def require_root_domain(fqdn):
    if fqdn.endswith('.'):
        return fqdn

    return f'{fqdn}.'


class SelectelAuthenticationRequired(ProviderException):
    def __init__(self, msg):
        message = 'Authorization failed. Invalid or empty token.'
        super().__init__(message)


class SelectelProvider(BaseProvider):
    SUPPORTS_GEO = False

    SUPPORTS = set(
        ('A', 'AAAA', 'ALIAS', 'CNAME', 'MX', 'NS', 'TXT', 'SRV', 'SSHFP')
    )

    MIN_TTL = 60

    PAGINATION_LIMIT = 50

    API_URL = 'https://api.selectel.ru/domains/v1'

    def __init__(self, id, token, *args, **kwargs):
        self.log = getLogger(f'SelectelProvider[{id}]')
        self.log.debug('__init__: id=%s', id)
        super().__init__(id, *args, **kwargs)

        self._sess = Session()
        self._sess.headers.update(
            {
                'X-Token': token,
                'Content-Type': 'application/json',
                'User-Agent': f'octodns/{octodns_version} octodns-selectel/{provider_version}',
            }
        )
        self._zone_records = {}
        self._domain_list = self.domain_list()
        self._zones = None

    def _request(self, method, path, params=None, data=None):
        self.log.debug('_request: method=%s, path=%s', method, path)

        url = f'{self.API_URL}{path}'
        resp = self._sess.request(method, url, params=params, json=data)

        self.log.debug('_request: status=%s', resp.status_code)
        if resp.status_code == 401:
            raise SelectelAuthenticationRequired(resp.text)
        elif resp.status_code == 404:
            return {}
        resp.raise_for_status()
        if method == 'DELETE':
            return {}
        return resp.json()

    def _get_total_count(self, path):
        url = f'{self.API_URL}{path}'
        resp = self._sess.request('HEAD', url)
        return int(resp.headers['X-Total-Count'])

    def _request_with_pagination(self, path, total_count):
        result = []
        for offset in range(0, total_count, self.PAGINATION_LIMIT):
            result += self._request(
                'GET',
                path,
                params={'limit': self.PAGINATION_LIMIT, 'offset': offset},
            )
        return result

    def _include_change(self, change):
        if isinstance(change, Update):
            existing = change.existing.data
            new = change.new.data
            new['ttl'] = max(self.MIN_TTL, new['ttl'])
            if new == existing:
                self.log.debug(
                    '_include_changes: new=%s, found existing=%s', new, existing
                )
                return False
        return True

    def _apply(self, plan):
        desired = plan.desired
        changes = plan.changes
        self.log.debug(
            '_apply: zone=%s, len(changes)=%d', desired.name, len(changes)
        )

        zone_name = desired.name[:-1]
        for change in changes:
            class_name = change.__class__.__name__
            getattr(self, f'_apply_{class_name}'.lower())(zone_name, change)

    def _apply_create(self, zone_name, change):
        new = change.new
        params_for = getattr(self, f'_params_for_{new._type}')
        for params in params_for(new):
            self.create_record(zone_name, params)

    def _apply_update(self, zone_name, change):
        self._apply_delete(zone_name, change)
        self._apply_create(zone_name, change)

    def _apply_delete(self, zone_name, change):
        existing = change.existing
        self.delete_record(zone_name, existing._type, existing.name)

    def list_zones(self):
        # This method is called dynamically in octodns.Manager._preprocess_zones()
        # and required for use of "*" if provider is source.
        zones_without_dot = self.domain_list()
        return [
            require_root_domain(zone_name) for zone_name in zones_without_dot
        ]

    def _params_for_multiple(self, record):
        for value in record.values:
            yield {
                'content': value,
                'name': record.fqdn,
                'ttl': max(self.MIN_TTL, record.ttl),
                'type': record._type,
            }

    def _params_for_single(self, record):
        yield {
            'content': record.value,
            'name': record.fqdn,
            'ttl': max(self.MIN_TTL, record.ttl),
            'type': record._type,
        }

    def _params_for_TXT(self, record):
        for value in record.values:
            yield {
                'content': unescape_semicolon(value),
                'name': record.fqdn,
                'ttl': max(self.MIN_TTL, record.ttl),
                'type': record._type,
            }

    def _params_for_MX(self, record):
        for value in record.values:
            yield {
                'content': value.exchange,
                'name': record.fqdn,
                'ttl': max(self.MIN_TTL, record.ttl),
                'type': record._type,
                'priority': value.preference,
            }

    def _params_for_SRV(self, record):
        for value in record.values:
            yield {
                'name': record.fqdn,
                'target': value.target,
                'ttl': max(self.MIN_TTL, record.ttl),
                'type': record._type,
                'port': value.port,
                'weight': value.weight,
                'priority': value.priority,
            }

    def _params_for_SSHFP(self, record):
        for value in record.values:
            yield {
                'name': record.fqdn,
                'ttl': max(self.MIN_TTL, record.ttl),
                'type': record._type,
                'algorithm': value.algorithm,
                'fingerprint_type': value.fingerprint_type,
                'fingerprint': value.fingerprint,
            }

    _params_for_A = _params_for_multiple
    _params_for_AAAA = _params_for_multiple
    _params_for_NS = _params_for_multiple

    _params_for_CNAME = _params_for_single
    _params_for_ALIAS = _params_for_single

    def _data_for_A(self, _type, records):
        return {
            'ttl': records[0]['ttl'],
            'type': _type,
            'values': [r['content'] for r in records],
        }

    _data_for_AAAA = _data_for_A

    def _data_for_NS(self, _type, records):
        return {
            'ttl': records[0]['ttl'],
            'type': _type,
            'values': [require_root_domain(r["content"]) for r in records],
        }

    def _data_for_MX(self, _type, records):
        values = []
        for record in records:
            values.append(
                {
                    'preference': record['priority'],
                    'exchange': require_root_domain(record["content"]),
                }
            )
        return {'ttl': records[0]['ttl'], 'type': _type, 'values': values}

    def _data_for_CNAME(self, _type, records):
        only = records[0]
        return {
            'ttl': only['ttl'],
            'type': _type,
            'value': require_root_domain(only["content"]),
        }

    _data_for_ALIAS = _data_for_CNAME

    def _data_for_TXT(self, _type, records):
        return {
            'ttl': records[0]['ttl'],
            'type': _type,
            'values': [escape_semicolon(r['content']) for r in records],
        }

    def _data_for_SRV(self, _type, records):
        values = []
        for record in records:
            values.append(
                {
                    'priority': record['priority'],
                    'weight': record['weight'],
                    'port': record['port'],
                    'target': require_root_domain(record["target"]),
                }
            )

        return {'type': _type, 'ttl': records[0]['ttl'], 'values': values}

    def _data_for_SSHFP(self, _type, records):
        values = []
        for record in records:
            values.append(
                {
                    'algorithm': record['algorithm'],
                    'fingerprint_type': record['fingerprint_type'],
                    'fingerprint': f'{record["fingerprint"]}',
                }
            )

        return {'type': _type, 'ttl': records[0]['ttl'], 'values': values}

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            'populate: name=%s, target=%s, lenient=%s',
            zone.name,
            target,
            lenient,
        )
        before = len(zone.records)
        records = self.zone_records(zone)
        if records:
            values = defaultdict(lambda: defaultdict(list))
            for record in records:
                name = zone.hostname_from_fqdn(record['name'])
                _type = record['type']
                if _type in self.SUPPORTS:
                    values[name][record['type']].append(record)
            for name, types in values.items():
                for _type, records in types.items():
                    data_for = getattr(self, f'_data_for_{_type}')
                    data = data_for(_type, records)
                    record = Record.new(
                        zone, name, data, source=self, lenient=lenient
                    )
                    zone.add_record(record)
        self.log.info(
            'populate:   found %s records', len(zone.records) - before
        )

    def domain_list(self):
        path = '/'
        domains = {}
        domains_list = []

        total_count = self._get_total_count(path)
        domains_list = self._request_with_pagination(path, total_count)

        for domain in domains_list:
            domains[domain['name']] = domain
        return domains

    def zone_records(self, zone):
        path = f'/{zone.name[:-1]}/records/'
        zone_records = []

        total_count = self._get_total_count(path)
        zone_records = self._request_with_pagination(path, total_count)

        self._zone_records[zone.name] = zone_records
        return self._zone_records[zone.name]

    def create_domain(self, name, zone=""):
        path = '/'

        data = {'name': name, 'bind_zone': zone}

        resp = self._request('POST', path, data=data)
        self._domain_list[name] = resp
        return resp

    def create_record(self, zone_name, data):
        self.log.debug('Create record. Zone: %s, data %s', zone_name, data)
        if zone_name in self._domain_list.keys():
            domain_id = self._domain_list[zone_name]['id']
        else:
            domain_id = self.create_domain(zone_name)['id']

        path = f'/{domain_id}/records/'
        return self._request('POST', path, data=data)

    def delete_record(self, domain, _type, zone):
        self.log.debug('Delete records. Domain: %s, Type: %s', domain, _type)
        domain_id = self._domain_list[domain]['id']
        records = self._zone_records.get(f'{domain}.', False)
        if not records:
            path = f'/{domain_id}/records/'
            records = self._request('GET', path)

        full_domain = f'{zone}.{domain}' if zone else domain
        delete_count, skip_count = 0, 0
        for record in records:
            if record['type'] == _type and record['name'] == full_domain:
                record_id = record["id"]
                path = f'/{domain_id}/records/{record_id}'
                try:
                    self._request('DELETE', path)
                    delete_count += 1
                except HTTPError:
                    skip_count += 1
                    self.log.warning(f'Failed to delete record {record_id}')

        self.log.debug(
            f'Deleted {delete_count} records. Skipped {skip_count} records'
        )
