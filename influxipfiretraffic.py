import argparse

from ipfire_traffic.IPFireTrafficSpeed import IPFireTrafficSpeed

parser = argparse.ArgumentParser(description="A tool to take network speed test and send the results to InfluxDB")
args = parser.parse_args()
collector = IPFireTrafficSpeed()
collector.run()
