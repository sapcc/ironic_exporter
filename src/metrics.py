from prometheus_client import Gauge, Counter


PortsGauge = Gauge('openstack_ironic_leftover_ports', 'Neutron ports corresponding to Ironic node ports that were not removed', ['node_uuid'])
CallbackGauge = Gauge('openstack_ironic_callback_state', 'Ironic node in wait call-back state', ['node_uuid'])
IrionicEventGauge = Gauge('openstack_ironic_event', 'Ironic node events', ['node_uuid', 'node_name', 'event'])
IrionicEventErrorCounter = Counter('openstack_ironic_errors', 'Ironic node errors', ['node_uuid', 'node_name'])
IronicProvisionState = Gauge('openstack_ironic_provision_state', 'Ironic node provision state', ['node_uuid', 'node_name'])


Provision_States = {
    "available": 0,
    "active": 1,
    "deploying": 2,
    "error": -1,
    "deploy failed": -2,
    "clean failed": -3,
    "wait call-back": -4
}
