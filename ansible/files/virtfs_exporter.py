#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtfs exporter
===============

Uses psutil and virtfs to combine disk/OS stats.

Dependency on packages:

* python3-libvirt
* libguestfs-tools

TODO:
  * Use python guestfs and inspectOS
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
from random import randrange
from time import sleep

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY
from prometheus_client.core import GaugeMetricFamily

try:
    from libvirtmetadata import LibvirtMetadata
except Exception:
    libvirtmetadata = None
try:
    from scheduler import Scheduler
except Exception:
    scheduler = None


class CustomCollector(object):
    def __init__(self, helper, helper_name='unknown', libv_meta=None):
        self.ALL_STATS = []
        self.HELPER = helper
        self.HELPER_NAME = helper_name
        self.libv_meta = libv_meta

    def collect(self):
        items = {}

        for stat in self.ALL_STATS:
            if stat[0] not in items:
                items[stat[0]] = []
            items[stat[0]].append(stat[1:])

        for key, values in items.items():
            labels = values[0][0]
            g = GaugeMetricFamily(key, self.HELPER, labels=labels)
            for labels, metadata, value in values:
                g.add_metric(metadata, value)
            yield g

        try:
            if self.libv_meta:
                g = GaugeMetricFamily(
                    'libvirt_connection_status',
                    'Libvirt status none (-1), connected (0), or error (1)',
                    labels=['node_exporter']
                )
                g.add_metric([self.HELPER_NAME], self.libv_meta.status)
                yield g
        except Exception:
            pass


def get_virtfs_df_pervolume(libv_meta):
    """
    Time/resource consuming - needs to run per hour or nightly
    not for peak detection, but rather for information.

    Virt-df starts read-only micro-instances with mounts and exports
    df data (display free disk data).
    Virt-df uses kB as unit for blocks.
    """
    try:
        rdb_data = libv_meta.get_rbd_metadata()
        data = {}
        metadata = {}
        for image in rdb_data:
            if image['format'] != 'raw':
                continue
            if any(not image.get(x) for x in [
                'format', 'protocol', 'username', 'path', 'domain'
            ]):
                continue

            # Prepare data structures
            if image['domain'] not in metadata:
                metadata[image['domain']] = {
                    'domain': image['domain'],
                    'name': image['name'],
                    'project': image['project'],
                    'uuid': image['uuid'],
                }

            if image['domain'] not in data:
                data[image['domain']] = {'variable': {},
                                         'storage_total': 0, 'storage_used': 0}

            disk_device = 'disk={}'.format(image.get('device', 'unknown'))
            disk_pool = 'pool={}'.format(image.get('pool', 'unknown'))
            disk_volume = 'volume={}'.format(image.get('volume', 'unknown'))

            device = ','.join([disk_device, disk_pool, disk_volume])
            if device not in data[image['domain']]['variable']:
                data[image['domain']]['variable'][device] = {
                    'disk_total': 0, 'disk_used': 0}

            # Try all monitor hosts or use break to go for different image
            for host in image.get('hosts', []):
                if not isinstance(host, str):
                    continue

                try:  # Subprocess to retrieve data
                    with tempfile.TemporaryDirectory(prefix='virtfs-exporter-', dir='/tmp') as tmpdir:
                        env = {'TMPDIR': tmpdir}
                        response = subprocess.run([  # SIGINT after 60s SIGKILL after 90s
                            'timeout', '--kill-after=90', '--signal=INT', '60', 'virt-df', '--csv', '-P', '1',
                            '--format={}'.format(image['format']),
                            '-a',
                            '{}://{}@{}/{}'.format(image['protocol'],
                                                   image['username'], host, image['path'])
                        ], stdout=subprocess.PIPE, env=env, check=True)  # timeout=60 - taken to lock on one only
                except PermissionError as e:
                    print('[ERROR] VIRT-DF Failed to cleanup tmp: {}'.format(str(e)))
                except subprocess.CalledProcessError as e:
                    print(
                        '[ERROR] VIRT-DF Exit: {} ({})'.format(image['path'], str(e)))
                    continue  # if subprocess returns non-zero exit status
                except subprocess.TimeoutExpired:
                    print('[ERROR] VIRT-DF Timeout: {}'.format(image['path']))
                    continue  # if timeout of subprocess - e.g. locked image

                try:  # Load csv from stdout
                    csv_file = response.stdout.decode(
                        'utf-8').strip().split('\n')
                    csv_reader = csv.DictReader(csv_file, delimiter=',')
                except Exception:
                    break  # try other image not other host

                # Load CSV data received from current host
                for row in csv_reader:
                    try:
                        data[image['domain']
                             ]['storage_total'] += int(row['1K-blocks'])
                        data[image['domain']
                             ]['storage_used'] += int(row['Used'])
                    except Exception:
                        pass
                    try:
                        data[image['domain']
                             ]['variable'][device]['disk_total'] += int(row['1K-blocks'])
                        data[image['domain']
                             ]['variable'][device]['disk_used'] += int(row['Used'])
                    except Exception:
                        pass
                    try:
                        part_prefix = image.get('device').replace('vd', 'sd')
                        part_code = os.path.split(
                            row['Filesystem'])[-1].replace(part_prefix, '').replace('sda', '')
                        try:
                            if part_code:
                                part_code = int(part_code)
                        except Exception:
                            pass
                        disk_partition = 'partition={}{}'.format(
                            part_prefix, part_code)
                        partition = ','.join(
                            [disk_partition, disk_pool, disk_volume])
                        data[image['domain']]['variable'][partition] = {
                            'partition_total': row['1K-blocks'],
                            'partition_used': row['Used'],
                        }
                    except Exception:
                        pass
                # If succesfully stored data using monitor host
                # break the hosts and go to next image
                break

        return data, metadata
    except Exception as e:
        print('[ERROR] Failed collecting disk data: {}'.format(str(e)))
    return {}


def stats_disks(libv_meta, cc):
    all_stats = []

    try:
        dsk_stats, metadata = get_virtfs_df_pervolume(libv_meta)
        for instance, stats in dsk_stats.items():
            try:
                all_stats.extend(libv_meta.export(
                    stats, instance, metadata=metadata[instance], prefix='virtfs_'))
                sleep(10)
            except Exception:
                pass
    except Exception:
        libv_meta.status = 1  # error

    cc.ALL_STATS = all_stats


def main(args):
    scheduler = Scheduler(max_workers=2)
    libv_meta = LibvirtMetadata()
    try:
        libv_meta.load_libvirt_metadata()
    except Exception:
        pass

    cc = CustomCollector('VirtFS instance stats',
                         helper_name='virtfs', libv_meta=libv_meta)
    REGISTRY.register(cc)
    start_http_server(args.port, addr=args.addr)
    scheduler.log(
        'Exposing metrics at: http://{}:{}/metrics'.format(args.addr, args.port))

    # Every day at 5am
    periodic_delay = {'hours': 2, 'minutes': randrange(120)}
    scheduler.add_periodic_task(
        stats_disks, 'day', periodic_delay=periodic_delay, run_now=args.run_now, args=(libv_meta, cc)
    )
    # Every 20 minutes - included in pervolume rbd request
    # scheduler.add_periodic_task(libv_meta.load_libvirt_metadata, 'minute', round=20)
    scheduler.run_concurrent(debug=args.debug)


def shell(args):
    """Start iPython shell for direct management access."""
    from IPython import embed
    from datetime import datetime as dt  # noqa
    from datetime import timedelta as td  # noqa
    from datetime import time  # noqa
    import logging
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    libv_meta = LibvirtMetadata()  # noqa
    embed(header="Welcome in iPython shell")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Virtfs textfile exporter')
    parser.set_defaults(func=main)
    subparsers = parser.add_subparsers(
        dest='action', help='Choose an alternative action (optional)')

    parser.add_argument(
        '-p', '--port', dest='port', default=9122, type=int,
        help='Port to expose metrics'
    )
    parser.add_argument(
        '-i', '--ip', dest='addr', default='0.0.0.0',
        help='IP address to expose metrics'
    )
    parser.add_argument('--run-now', dest='run_now',
                        action='store_true', help='Run now and then continue')
    parser.add_argument('--disk', dest='disk',
                        action='store_true', help='Measure disk space (24h)')
    parser.add_argument('-o', '--output', dest='output',
                        default=sys.stdout, help='Output file (Default stdout)')
    parser.add_argument('--debug', dest='debug',
                        action='store_true', help='Debug messages')

    subparsers.add_parser(
        'shell', help='Run iPython shell').set_defaults(func=shell)

    args = parser.parse_args()
    args.func(args)
