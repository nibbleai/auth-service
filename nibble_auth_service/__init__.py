import logging

LOG_FILE = '/var/log/nibble_auth.log'
FORMAT = '%(asctime)s | %(levelname)s\t%(message)s'

logging.basicConfig(
    filename=LOG_FILE,
    format=FORMAT
)
