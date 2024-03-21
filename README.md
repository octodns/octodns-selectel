# Selectel DNS provider for octoDNS

An [octoDNS](https://github.com/octodns/octodns/) provider that targets [Selectel DNS](https://docs.selectel.com/cloud-services/dns-hosting/dns_hosting/).

## Contents

* [Installation](#installation)
* [Capabilities](#capabilities)
* [Configuration](#configuration)
* [Quickstart](#quickstart)
* [Current provider vs. Legacy provider](#current-provider-vs-legacy-provider)
* [Migration from legacy DNS API](#migration-from-legacy-dns-api)
* [Development](#development)

## Installation
Install Selectel plugin in your environment and [octodns](https://github.com/octodns/octodns) itself if it is not present.

```bash
pip install octodns octodns-selectel
```

## Capabilities

| What              | Value                                             |
|-------------------|---------------------------------------------------|
| Supported records | A, AAAA, ALIAS, CAA, CNAME, DNAME, MX, NS, SRV, SSHFP, TXT    |
| Dynamic records   | ❌ |

## Configuration
Add selectel provider to `config.yaml`.
```yaml
providers:
  selectel:
    class: octodns_selectel.SelectelProvider
    token: env/KEYSTONE_PROJECT_TOKEN
```
Set **KEYSTONE_PROJECT_TOKEN** environmental variable or write value directly in config without `env/` prefix.  
How to obtain required token you can read [here](https://developers.selectel.com/docs/control-panel/authorization/#project-token)
## Quickstart
To get more details on configuration and capabilities check [octodns repository](https://github.com/octodns/octodns)
#### 1. Organize your configs.
```bash
Project
└── .octodns
    ├── config.yaml
    └── zones
        ├── octodns-test-alias.com.yaml
        └── octodns-test.com.yaml

```
#### 2. Fill octodns configuration file
```yaml
# .octodns/config.yaml
providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: ./octodns/zones
    default_ttl: 3600
    enforce_order: True
  selectel:
    class: octodns_selectel.SelectelProvider
    token: env/KEYSTONE_PROJECT_TOKEN

zones:
  octodns-test.com.:
    sources:
      - config
    targets:
      - selectel
  octodns-test-alias.com.:
    sources:
      - config
    targets:
      - selectel
```
#### 3. Prepare config for each of your zones
```yaml
# .octodns/zones/octodns-test.com.yaml
'':
  - ttl: 3600
    type: A
    values:
      - 1.2.3.4
      - 1.2.3.5
  - ttl: 3600
    type: AAAA
    values: 
      - 6dc1:b9af:74ca:84e9:6c7c:5c0f:c292:9188
      - 5051:e345:9038:052c:00db:eb98:d871:8ae6
  - ttl: 3600
    type: MX
    value:
      exchange: mail1.octodns-test.com.
      preference: 10
  - ttl: 3600
    type: TXT
    values: 
      - "bar"
      - "foo"

_sip._tcp:
  - ttl: 3600
    type: SRV
    values:
    - port: 5060
      priority: 10
      target: phone1.example.com.
      weight: 60
    - port: 5030
      priority: 20
      target: phone2.example.com.
      weight: 0     

caa:
  - ttl: 3600
    type: CAA
    values:
    - flags: 0
      tag: issue
      value: octodns-test.com.

dname:
  - ttl: 3600
    type: DNAME
    value: octodns-test.com.

foo:
  - ttl: 3600
    type: CNAME
    value: bar.octodns-test.com.

sshfp:
  - ttl: 3600
    type: SSHFP
    values:
    - algorithm: 1
      fingerprint: "4158f281921260b0205508121c6f5cee879e15f22bdbc319ef2ae9fd308db3be"
      fingerprint_type: 2
    - algorithm: 4
      fingerprint: "123456789abcdef67890123456789abcdef67890123456789abcdef123456789"
      fingerprint_type: 2

txt:
  - ttl: 3600
    type: TXT
    values: 
      - "bar_txt"
      - "foo_txt"
```
```yaml
# .octodns/zones/octodns-test-alias.com.yaml
'':
  - ttl: 3600
    type: ALIAS
    value: octodns-test.com.
```
#### 4. Check and apply!
```bash
# Run config and check suggested changes
octodns-sync --config-file=.octodns/config.yaml
# Apply changes if everything is ok by adding
octodns-sync --config-file=.octodns/config.yaml --doit
```

### Current provider vs. Legacy provider
Current provider is `octodns_selectel.SelectelProvider`  
Legacy provider is `octodns_selectel.SelectelProviderLegacy`  

They are not compatible. They utilize different API and created zones live on different authoritative servers.
Zone created in v2 API with current provider is entirely new zone, and not available via v1 api and vice versa.  

If you are going to create new zone, we strongly recommend to use `SelectelProvider`.  
If you have zones in v1, you still can manage them with `SelectelLegacyProvider`.

If you updated plugin from unstable (0.x.x) version you should rename provider class in octodns config from `SelectelProvider` to `SelectelLegacyProvider` 
to work with legacy api.

### Migration from legacy DNS API
If v1 API is still available for you and your zones are hosted there, then you probably would like to move your zones to v2. Legacy API will be eventually shutdown.  
With octodns you can sync ALL your v1 zone with v2 by using both providers as in example below.  
❗️IMPORTANT❗️  
`SELECTEL_TOKEN` and `KEYSTONE_PROJECT_TOKEN` are **different** tokens!  
Above we mentioned how to get keystone token, how to obtain selectel token read [here](https://developers.selectel.com/docs/control-panel/authorization/#selectel-token-api-key)
```yaml
processors:
  # Selectel doesn't allow manage Root NS records
  # for skipping root ns use IgnoreRootNsFilter class
  no-root-ns:
    class: octodns.processor.filter.IgnoreRootNsFilter

providers:
  selectel_legacy:
    class: octodns_selectel.SelectelProviderLegacy
    token: env/SELECTEL_TOKEN
  selectel:
    class: octodns_selectel.SelectelProvider
    token: env/KEYSTONE_PROJECT_TOKEN

zones:
  # Using '*' to sync all zones available on account.
  "*":
    sources:
      - selectel_legacy
    processors:
    - no-root-ns
    targets:
      - selectel
```

## Development
See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.
