#!/usr/bin/env python
import logging
import json
from threading import Thread
from datetime import datetime
from retry import retry

import pika

import metrics

LOG = logging.getLogger(__name__)


class Notifications(Thread):

    def __init__(self, user, password, region, routing_key, use_own_channel = False):
        Thread.__init__(self)
        self.routing_key = routing_key
        self.use_own_channel = use_own_channel
        self.region = region
        self.credentials = pika.PlainCredentials(user, password)
        self.nodes_status = {}
        self.connection = None
        self.channel = None

    @retry((pika.exceptions.AMQPConnectionError,
        pika.exceptions.ConnectionClosedByBroker), delay=5, jitter=(1, 3))
    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = f'ironic-rabbitmq.monsoon3.svc.kubernetes.{self.region}.cloud.sap',
            credentials=self.credentials))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        channel_name = f'ironic_versioned_notifications.{self.routing_key}'
        if self.use_own_channel:
            channel_name = f'ironic_exporter_notification.{self.routing_key}'
            self.channel.queue_declare(queue=channel_name, auto_delete=True)
        self.nodes_status = {}

        try:
            self.channel.queue_bind(exchange='ironic',
                queue=channel_name,
                routing_key = f'ironic_versioned_notifications.{self.routing_key}')
            self.channel.basic_consume(
                queue=channel_name,
                on_message_callback=self._callback,
                auto_ack=True
            )
        except pika.exceptions.ChannelClosed as e:
            if e.args[0] == 404:
                LOG.info("channel: %s NOT FOUND",channel_name)
                #No need to retry or start consuming!
                return
            raise e

        try:
            self.channel.start_consuming()

        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.connection.close()

        # Don't recover connections closed by server
        except pika.exceptions.ConnectionClosedByBroker as e:
            LOG.error("ConnectionClosedByBroker: Channel: %s",channel_name)
            #Retry to connect
            raise e


    def _callback(self, ch, method, properties, body):
        try:
            notification = json.loads(body)
            msg = json.loads(notification['oslo.message'])
            self._handle_events(msg)
            self._set_provision_state(msg)
        except KeyError as err:
            LOG.error("Cannot read ironic event json payload: %s",err)


    def _set_provision_state(self, msg):
        provision_state = msg['payload']['ironic_object.data']['provision_state']
        node_id = msg['payload']['ironic_object.data']['uuid']
        node_name = msg['payload']['ironic_object.data']['name']
        if provision_state in metrics.Provision_States:
            metrics.IronicProvisionState.labels(node_id, node_name).set(metrics.Provision_States[provision_state])


    def _handle_events(self, msg):
        try:
            event_type = msg['event_type'].split('.')
            LOG.debug(event_type)
            timestamp = msg['timestamp']
            date_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            data = msg['payload']['ironic_object.data']
            node_id = data['uuid']
            node_name = data['name']
            provision_state = data['provision_state']
        except KeyError as err:
            LOG.error("Cannot read ironic event json payload: %s", err)
            return

        if node_name is None:
            return

        if node_id not in self.nodes_status:
            self.nodes_status[node_id] = {}

        if event_type[3] != 'error':
            LOG.info('ironic_notification_info: %s: %s - %s - %s. provision_state: %s',node_name, event_type[1], event_type[2], event_type[3], provision_state)
            if event_type[3] == 'start':
                self.nodes_status[node_id][event_type[2]] = timestamp
                LOG.debug(self.nodes_status)
            if event_type[3] == 'end' or event_type[3] == 'success':
                LOG.info(self.nodes_status[node_id])
                if event_type[2] in self.nodes_status[node_id]:
                    start_time = datetime.strptime(self.nodes_status[node_id][event_type[2]], '%Y-%m-%d %H:%M:%S.%f')
                    delta_time = date_time - start_time
                    event_label = f'{event_type[1]}_{event_type[2]}'
                    metrics.IrionicEventGauge.labels(node_id, node_name, event_label).set(delta_time.seconds)
                    
        elif event_type[3] == 'error':
            target_provision_state = data['target_provision_state']
            LOG.error('ironic_notification_error: %s: %s - %s - %s. provision_state: %s. target_provision_state: %s',node_name, event_type[1], event_type[2], event_type[3], provision_state, target_provision_state)
            metrics.IrionicEventErrorCounter.labels(node_id, node_name).inc()
