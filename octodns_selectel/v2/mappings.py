from string import Template

from octodns_selectel.escaping_semicolon import (
    escape_semicolon,
    unescape_semicolon,
)

from .exceptions import SelectelException


def to_selectel_rrset(record):
    rrset = dict(name=record.fqdn, ttl=record.ttl, type=record._type)
    rrset_records = []
    content_caa_tmpl = Template("$flag $tag \"$value\"")
    content_mx_tmpl = Template("$preference $exchange")
    content_srv_tmpl = Template("$priority $weight $port $target")
    content_sshfp_tmpl = Template("$algorithm $fingerprint_type $fingerprint")
    if record._type in {"A", "AAAA", "NS"}:
        rrset_records = list(
            map(lambda value: {'content': value}, record.values)
        )
    elif record._type in {"CNAME", "ALIAS", "DNAME"}:
        rrset_records = [{'content': record.value}]
    elif record._type == "TXT":
        rrset_records = [
            dict(content=f'\"{unescape_semicolon(value)}\"')
            for value in record.values
        ]
    elif record._type == "CAA":
        rrset_records = [
            dict(
                content=content_caa_tmpl.substitute(
                    flag=value.flags, tag=value.tag, value=value.value
                )
            )
            for value in record.values
        ]
    elif record._type == "MX":
        rrset_records = list(
            map(
                lambda value: {
                    'content': content_mx_tmpl.substitute(
                        preference=value.preference, exchange=value.exchange
                    )
                },
                record.values,
            )
        )
    elif record._type == "SRV":
        rrset_records = list(
            map(
                lambda value: {
                    'content': content_srv_tmpl.substitute(
                        priority=value.priority,
                        weight=value.weight,
                        port=value.port,
                        target=value.target,
                    )
                },
                record.values,
            )
        )
    elif record._type == "SSHFP":
        rrset_records = list(
            map(
                lambda value: {
                    'content': content_sshfp_tmpl.substitute(
                        algorithm=value.algorithm,
                        fingerprint_type=value.fingerprint_type,
                        fingerprint=value.fingerprint,
                    )
                },
                record.values,
            )
        )
    else:
        raise SelectelException(
            f'DNS Record with type: {record._type} not supported'
        )
    rrset["records"] = rrset_records
    return rrset


def to_octodns_record_data(rrset):
    rrset_type = rrset["type"]
    octodns_record = dict(type=rrset_type, ttl=rrset["ttl"])
    record_values = []
    key_for_record_values = "values"
    if rrset_type in {"A", "AAAA", "NS"}:
        record_values = [r['content'] for r in rrset["records"]]
    elif rrset_type in {"CNAME", "ALIAS", "DNAME"}:
        key_for_record_values = "value"
        record_values = rrset["records"][0]["content"]
    elif rrset_type == "TXT":
        record_values = [
            escape_semicolon(r['content']).strip('"\'')
            for r in rrset["records"]
        ]
    elif rrset_type == "CAA":
        for record in rrset["records"]:
            flag, tag, value = record["content"].split(" ", 2)
            record_values.append(
                {'flags': flag, 'tag': tag, 'value': value.strip('"')}
            )
    elif rrset_type == "MX":
        for record in rrset["records"]:
            preference, exchange = record["content"].split(" ")
            record_values.append(
                {'preference': preference, 'exchange': exchange}
            )
    elif rrset_type == "SRV":
        for record in rrset["records"]:
            priority, weight, port, target = record["content"].split(" ")
            record_values.append(
                {
                    'priority': priority,
                    'weight': weight,
                    'port': port,
                    'target': target,
                }
            )
    elif rrset_type == "SSHFP":
        for record in rrset["records"]:
            algorithm, fingerprint_type, fingerprint = record["content"].split(
                " "
            )
            record_values.append(
                {
                    'algorithm': algorithm,
                    'fingerprint_type': fingerprint_type,
                    'fingerprint': fingerprint,
                }
            )
    else:
        raise SelectelException(
            f'DNS Record with type: {rrset_type} not supported'
        )
    octodns_record[key_for_record_values] = record_values
    return octodns_record
