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

from datetime import datetime
from datetime import timedelta
from oslo_utils import timeutils
import time

from oslo_config import cfg
from oslo_log import log
import requests

from watcher.datasource import base
from watcher.common import exception

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class PrometheusHelper(base.DataSourceBase):

    NAME = 'prometheus'
    METRIC_MAP = base.DataSourceBase.METRIC_MAP['prometheus']

    def __init__(self):
        pass

    def _timestamps(self, start_time, end_time):

        def _format_timestamp(_time):
            if _time:
                if isinstance(_time, datetime.datetime):
                    return _time.isoformat('T') + "Z"
                return _time
            return None

        start_timestamp = _format_timestamp(start_time)
        end_timestamp = _format_timestamp(end_time)

        if ((start_timestamp is not None) and (end_timestamp is not None) and
                (timeutils.parse_isotime(start_timestamp) >
                 timeutils.parse_isotime(end_timestamp))):
            raise exception.Invalid(
                _("Invalid query: %(start_time)s > %(end_time)s") % dict(
                    start_time=start_timestamp, end_time=end_timestamp))
        return start_timestamp, end_timestamp

    def query_retry(self, f, url, **kwargs):
        for i in range(CONF.prometheus_client.query_max_retries):
            try:
                return f(url, params=kwargs)
            except Exception as e:
                LOG.exception(e)
                time.sleep(CONF.prometheus_client.query_timeout)

    def statistic_aggregation(self, resource_id=None, meter_name=None,
                              period=300, granularity=100, dimensions=None,
                              aggregation='mean', group_by='*'):
        """Representing a statistic aggregate by operators

               :param resource_id: id of resource to list statistics for.
               :param meter_name: meter name of which we want the statistics.
               :param period: Period in seconds over which to group samples.
               :param granularity: frequency of marking metric point, in seconds.
               :param dimensions: dimensions (dict). This param isn't used in
                                  Gnocchi datasource.
               :param aggregation: Should be chosen in accordance with policy
                                   aggregations.
               :param group_by: list of columns to group the metrics to be returned.
                                This param isn't used in Gnocchi datasource.
               :return: value of aggregated metric
               """

        stop_time = datetime.utcnow() - timedelta(hours=(int(8)))
        start_time = stop_time - timedelta(seconds=(int(period)))

        start_timestamp, end_timestamp = self._timestamps(start_time,
                                                          stop_time)

        if meter_name == 'hardware.memory.used':
            meter_name = 'mem_total'

        url = CONF.prometheus_client.prometheus_url
        raw_kwargs = dict(
            query=meter_name + '{host="' + resource_id + '"}',
            start=start_timestamp,
            end=end_timestamp,
            step=granularity,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        response = self.query_retry(
            f=requests.get, url=url, **kwargs)

        if not response:
            LOG.warning("The {0} resource {1} could not be "
                        "found".format(self.NAME, resource_id))

        values = response.json().get('data').get('result')[0].get('values')
        result = 0
        for i in values:
            temp = i[1]
            result = result + temp

        result = result / 4
        return result


