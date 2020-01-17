# Prometheus-VirtFS-Exporter Charm

Charm can relate to prometheus using a preferred endpoint `target` or alternatively `manual-jobs`.
Preferred endpoint assures that all units are in the same group, while manual jobs get unique names by prometheus.

## Build

Build with patched interface for juju-info. (https://github.com/juju-solutions/interface-juju-info/pull/6)

```
CHARM_INTERFACES_DIR=./interfaces charm-build
```

## Bundle example

```
series: xenial
applications:
  prometheus:
    charm: cs:bionic/prometheus2-12
    num_units: 1
  virtfs-exporter:
    charm: /tmp/charm-builds/prometheus-virtfs-exporter
    options:
      debug: true
  ubuntu:
    charm: cs:ubuntu
    num_units: 2
relations:
- - virtfs-exporter:prometheus-target
  - prometheus:target
- - ubuntu:juju-info
  - virtfs-exporter:nova-compute
```
