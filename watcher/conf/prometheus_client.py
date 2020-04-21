# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

prometheus_client = cfg.OptGroup(name='prometheus_client',
                                 title='Configuration Options for Prometheus')

PROMETHEUS_CLIENT_OPTS = [
    cfg.StrOpt('prometheus_url',
               help='Configure prometheus API address'),
    cfg.StrOpt('region_name',
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.'),
    cfg.IntOpt('query_max_retries',
               default=10,
               mutable=True,
               help='How many times Watcher is trying to query again'),
    cfg.IntOpt('query_timeout',
               default=1,
               mutable=True,
               help='How many seconds Watcher should wait to do query again')]


def register_opts(conf):
    conf.register_group(prometheus_client)
    conf.register_opts(PROMETHEUS_CLIENT_OPTS, group=prometheus_client)


def list_opts():
    return [('prometheus_client', PROMETHEUS_CLIENT_OPTS)]
