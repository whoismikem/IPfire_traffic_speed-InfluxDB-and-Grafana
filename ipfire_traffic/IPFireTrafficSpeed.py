import sys
import time

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests import ConnectTimeout, ConnectionError

from ipfire_traffic.common import log
from ipfire_traffic.config import config

import time
import os
import json
# import datetime



class IPFireTrafficSpeed():
    def __init__(self):
        self.influx_client = self._get_influx_connection()

        self.time_current = time.time()
        self.time_last = time.time()
        self.rxb_current = 0
        self.rxb_last = 0
        self.txb_current = 0
        self.txb_last = 0
        self.rpkt_last = 0
        self.tpkt_last = 0
        self.rpkt_current = 0
        self.tpkt_current = 0
        
        self.first_try = True

    def _get_influx_connection(self):
        """
        Create an InfluxDB connection and test to make sure it works.
        We test with the get all users command.  If the address is bad it fails
        with a 404.  If the user doesn't have permission it fails with 401
        :return:
        """

        influx = InfluxDBClient(
            config.influx_address,
            config.influx_port,
            database=config.influx_database,
            ssl=config.influx_ssl,
            verify_ssl=config.influx_verify_ssl,
            username=config.influx_user,
            password=config.influx_password,
            timeout=5
        )
        try:
            log.debug('Testing connection to InfluxDb using provided credentials')
            influx.get_list_users()  # TODO - Find better way to test connection and permissions
            log.debug('Successful connection to InfluxDb')
        except (ConnectTimeout, InfluxDBClientError, ConnectionError) as e:
            if isinstance(e, ConnectTimeout):
                log.critical('Unable to connect to InfluxDB at the provided address (%s)', config.influx_address)
            elif e.code == 401:
                log.critical('Unable to connect to InfluxDB with provided credentials')
            else:
                log.critical('Failed to connect to InfluxDB for unknown reason')

            sys.exit(1)

        return influx

    def write_influx_data(self, json_data):
        """
        Writes the provided JSON to the database
        :param json_data:
        :return: None
        """
        log.debug(json_data)

        try:
            self.influx_client.write_points(json_data)
        except (InfluxDBClientError, ConnectionError, InfluxDBServerError) as e:
            if hasattr(e, 'code') and e.code == 404:
                log.error('Database %s Does Not Exist.  Attempting To Create', config.influx_database)
                self.influx_client.create_database(config.influx_database)
                self.influx_client.write_points(json_data)
                return

            log.error('Failed To Write To InfluxDB')
            print(e)

        log.debug('Data written to InfluxDB')

    def send_results(self, results):
        """
        Formats the payload to send to InfluxDB
        :rtype: None
        """
        result_dict = results

        input_points = [
            {
                'measurement': 'IPFireTraffic',
                'fields': {
                    'download_bytes': result_dict['rx_bytes'],
                    'upload_bytes': result_dict['tx_bytes'],
                    'download_packets': result_dict['rpkt_count'],
                    'upload_packets': result_dict['tpkt_count']
                }
            }
        ]

        print(f'Sending data to influxdb: {input_points}')
        self.write_influx_data(input_points)


    def get_bytes(self):
        try:
            
            shell_cmd = f'ip -j -s link show {config.interface_name}'
            print(f'CMD: {shell_cmd}')
            # shell_cmd = '/Users/michal/Desktop/speed.cgi'
            std_out = os.popen(shell_cmd)
            output = std_out.read()
            json_output = json.loads(output)

            json_stats = json_output[0]['stats64']
            rx_bytes = json_stats['rx']['bytes']
            rx_packets = json_stats['rx']['packets']
            rx_errors = json_stats['rx']['errors']

            tx_bytes = json_stats['tx']['bytes']
            tx_packets = json_stats['tx']['packets']
            tx_errors = json_stats['tx']['errors']


            self.time_current = time.time()
            time_diff = self.time_current - self.time_last
            self.time_last = self.time_current

            

            print(json_output)
            
            # Receive
            self.rxb_current = rx_bytes
            rxb_diff = self.rxb_current - self.rxb_last
            self.rxb_last = self.rxb_current
            rx_final_bytes = rxb_diff / time_diff
            # Send
            self.txb_current = tx_bytes
            txb_diff = self.txb_current - self.txb_last
            self.txb_last = self.txb_current
            tx_final_bytes = txb_diff / time_diff

            # Packets Receive
            self.rpkt_current = rx_packets
            rpkt_diff = self.rpkt_current - self.rpkt_last
            self.rpkt_last = self.rpkt_current
            rpkt_final_count = rpkt_diff / time_diff
            # Packet Send
            self.tpkt_current = tx_packets
            tpkt_diff = self.tpkt_current - self.tpkt_last
            self.tpkt_last = self.tpkt_current
            tpkt_final_count = tpkt_diff / time_diff

            result_dict = {
                'rx_bytes': round(rx_final_bytes, 2),
                'tx_bytes': round(tx_final_bytes, 2),
                'rpkt_count': round(rpkt_final_count, 2),
                'tpkt_count': round(tpkt_final_count, 2),
                    }
            print(f'Result dict: {result_dict}')
            return result_dict
    
        except Exception as err:
            print(f'Error occured here: {err}')
    
    def run(self):
        while True:
            print("Starting in run")
            bytes_dict =  self.get_bytes()
            if not self.first_try:
                self.send_results(bytes_dict)
                
            self.first_try = False

            print(bytes_dict)
            log.info('Waiting %s seconds until next test', config.delay)
            time.sleep(config.delay)
