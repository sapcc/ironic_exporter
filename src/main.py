from time import sleep
import logging
import os
import sys

from prometheus_client import start_http_server, Info, CollectorRegistry
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

import config

from ironic_notifications import Notifications
from ironic_ports import Ports

PORT_NUMBER = os.environ.get("PORT_NUMBER", 9191)
LOG = logging.getLogger(__name__)


def setup_logging():
    """
    Setup logging
    """
    logging.basicConfig(
        format='%(asctime)-15s %(process)d %(levelname)s %(filename)s:%(lineno)d %(message)s',
        level=os.environ.get("LOGLEVEL", "INFO")
    )


def setup_k8s():
    """
    setup k8s client env vars
    """
    try:
        k8s_config.load_kube_config()

    except k8s_config.config_exception.ConfigException:
        os.environ['KUBERNETES_SERVICE_HOST'] = os.environ['KUBERNETES_SERVICE_HOST'] or 'kubernetes.default'
        os.environ['KUBERNETES_SERVICE_PORT'] = os.environ['KUBERNETES_SERVICE_PORT'] or 443
        k8s_config.load_incluster_config()


def setup_prometheus():
    """
    Setup prometheus
    """
    port_info = Info('openstack_ironic_leftover_ports',
                     'Neutron ports corresponding to Ironic node ports that were not removed')
    port_info.info({'version': os.environ.get("OS_VERSION", '')})
    registry = CollectorRegistry()
    registry.register(port_info)


def setup_openstack_clis():
    """
    setup openstack clients (neutron and ironic)
    """
    try:
        neutron_cli = config.get_neutron_client()
        ironic_cli = config.get_ironic_client()
        return neutron_cli, ironic_cli

    except k8s_client.rest.ApiException as err:
        if err.status == 404:
            LOG.error("Neutron-etc configmap not found!")
            sys.exit(1)
        else:
            LOG.error("Cannot load neutron configmap: %s",err)
            sys.exit(1)


if __name__ == "__main__":

    setup_logging()
    setup_k8s()
    setup_prometheus()

    rabbit_auth = config.get_rabbitmq_auth()
    region = os.environ.get("REGION", "qa-de-1")


    notifications_enabled = os.environ.get("NOTIFICATIONS", False)

    if notifications_enabled:
        for routing_key in ["info", "error"]:
            notifications = Notifications(rabbit_auth[0], rabbit_auth[1], region, routing_key)
            notifications.setDaemon(True)
            notifications.start()


    ports = Ports(*setup_openstack_clis())

    try:
        start_http_server(int(PORT_NUMBER), addr='0.0.0.0')
        while True:
            LOG.info("-----------------------Start Query------------------------")
            ports.start_ironic_nodes_query()
            sleep(600)
    except KeyboardInterrupt:
        sys.exit(0)
