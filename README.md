# ironic_exporter

This is a exporter for openstack ironic, which exports the following metrics:

- openstack_ironic_leftover_ports: Neutron ports corresponding to Ironic node ports that were not removed
- openstack_ironic_event: Ironic node events (via Ironic Notifications)
- openstack_ironic_errors: Ironic node errors per node (via Ironic Notifications)
- openstack_ironic_provision_state: Ironic node provision state (via Ironic Notifications)
