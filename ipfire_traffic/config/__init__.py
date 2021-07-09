import os

from ipfire_traffic.config.configmanager import ConfigManager

if os.getenv('ipfiretrafficspeed'):
    config = os.getenv('ipfiretrafficspeed')
else:
    config = 'config.ini'

config = ConfigManager(config)