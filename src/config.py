import logging
import os
from io import StringIO
import re

from kubernetes import client as k8s_client
from keystoneauth1 import identity
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutron_client
from ironicclient import client as ironic_client
from backports import configparser

LOG = logging.getLogger(__name__)

def get_neutron_client():
    """
    Neutron client
    """

    auth_parser = get_client_auth()

    auth = identity.Password(auth_url=auth_parser['www_authenticate_uri'],
                             username=auth_parser["username"],
                             password=auth_parser["password"],
                             project_name=auth_parser["project_name"],
                             project_domain_name=auth_parser["user_domain_name"],
                             user_domain_name=auth_parser["user_domain_name"])

    sess = session.Session(auth=auth)

    return neutron_client.Client(session=sess)

def get_ironic_client():
    """
    Ironic Client
    """

    auth_parser = get_client_auth()

    auth = identity.Password(auth_url=auth_parser['www_authenticate_uri'],
                            username=os.environ.get("OS_IRONIC_USERNAME", "ipmi_exporter"),
                            password=os.environ.get("OS_IRONIC_PASSWORD", ""),
                            project_name=os.environ.get("OS_PROJECT_NAME", "master"),
                            project_domain_name=os.environ.get("OS_PROJECT_DOMAIN_NAME", "ccadmin"),
                            user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME", "Default"))
    sess = session.Session(auth=auth)

    return ironic_client.Client(version=1, session=sess)

def get_client_auth():
    """
    get keystone auth token
    """
    v1 = k8s_client.CoreV1Api()
    cfg = v1.read_namespaced_config_map("neutron-etc", "monsoon3")
    parser = configparser.ConfigParser()
    parser.read_string(cfg.data["neutron.conf"])

    return parser["keystone_authtoken"]

def get_rabbitmq_auth():
    """
    get rabit mq auth
    """
    v1 = k8s_client.CoreV1Api()
    cfg = v1.read_namespaced_config_map("ironic-rabbitmq-bin", "monsoon3")
    string = cfg.data["rabbitmq-start"]
    buf = StringIO(string)

    while True:
        line = buf.readline()
        if line.find('"rabbitmq"') > 0:
            user_pw = re.findall(r'\"(.+?)\"',line)
            return user_pw

        if not line:
            break
