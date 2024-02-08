import logging
import metrics

LOG = logging.getLogger(__name__)


class Ports:


    def __init__(self, neutron_cli, ironic_cli):
        self.neutron_cli = neutron_cli
        self.ironic_cli = ironic_cli


    def get_available_ironic_nodes_uuid(self):
        LOG.debug("Quering Ironic for all non deployed (available) Ironic Nodes") 
        available_nodes = self.ironic_cli.node.list(maintenance=False,
                                        fields=['uuid', 'provision_state', 'maintenance'])
        LOG.debug("Found %d available nodes" % len(available_nodes))
        return available_nodes


    def set_leftover_ports(self, node):
        leftover_neutron_ports = {}
        if node.provision_state != 'available':
            LOG.debug("Remove Ironic Node uuid %s",node.uuid)
            try:
                metrics.PortsGauge.labels(node.uuid).set(0)
            except KeyError as err:
                LOG.error("Cannot set Ironic Node label err: %s",err)
            return

        all_node_ports = self.ironic_cli.port.list(node=node.uuid)
        leftover_neutron_ports[node.uuid] = []

        for port in all_node_ports:
            LOG.debug("Port MAC address is %s",port.address)
            neutron_ports = self.neutron_cli.list_ports(mac_address=port.address)['ports']

            if len(neutron_ports) == 1:
                LOG.info("node_uuid: %s: leftover port_id: %s",node.uuid, neutron_ports[0]['id'])
                leftover_neutron_ports[node.uuid].append(neutron_ports[0]['id'])

            elif len(neutron_ports) > 1:
                LOG.error("There is more than on Neutron port with mac %s",port.address)
                for leftover_port in neutron_ports:
                    LOG.info("node_uuid: %s: leftover port_id: %s",node.uuid, leftover_port['id'])
                    leftover_neutron_ports[node.uuid].append(leftover_port['id'])
        
        try:
            metrics.PortsGauge.labels(node.uuid).set(len(leftover_neutron_ports[node.uuid]))
        except KeyError as err:
            LOG.error("Cannot set Ironic Node label err: %s",err)


    def set_wait_callback_state(self, node):
        if node.provision_state == 'wait call-back':
            metrics.CallbackGauge.labels(node.uuid).set(1)
        else:
            metrics.CallbackGauge.labels(node.uuid).set(0)
            #cleaning state


    def start_ironic_nodes_query(self):
        """
        Do query in Ironic and after in Neutron to find leftover ports
        """

        all_nodes = self.get_available_ironic_nodes_uuid()

        if len(all_nodes) == 0:
            return

        for node in all_nodes:
            LOG.debug(f"Ironic Node uuid is {node.uuid}")
            self.set_leftover_ports(node)
            self.set_wait_callback_state(node)