# Prometheus-VirtFS-Exporter Charm

Charm can relate to prometheus using a preferred endpoint `target` or alternatively `manual-jobs`.
Preferred endpoint assures that all units are in the same group, while manual jobs get unique names by prometheus.

## Usage

Exporter gathers metrics from nova-compute and libguestfs tools. This charm relates to the prometheus charm on the `scrape` interface, and provides a metrics endpoint for prometheus to scrape and is deployed as a subordinate on nova-compute:

```
juju deploy cs:~huntdatacenter/prometheus-virtfs-exporter virtfs-exporter
juju add-relation nova-compute:juju-info virtfs-exporter:nova-compute
juju add-relation prometheus:scrape virtfs-exporter:prometheus-target
```

## Development

Here are some helpful commands to get started with development and testing:

```
$ make help
lint                 Run linter
build                Build charm
deploy               Deploy charm
upgrade              Upgrade charm
force-upgrade        Force upgrade charm
test-xenial-bundle   Test Xenial bundle
test-bionic-bundle   Test Bionic bundle
push                 Push charm to stable channel
clean                Clean .tox and build
help                 Show this help
```
