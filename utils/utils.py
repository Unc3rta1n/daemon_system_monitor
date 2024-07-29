import argparse
import configparser
import logging


def parse_args():
    parser = argparse.ArgumentParser(description="Демон Системный монитор")
    parser.add_argument("-port", type=int, help="Порт, на котором хотите развернуть демона")
    _args = parser.parse_args()
    return _args


def init_logging():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console_handler])


def get_config():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    return config


def configure_daemon():
    config = get_config()
    settings = {
        'filesystem_info': bool(config["Settings"]["filesystem_info"]),
        'cpu_info': bool(config["Settings"]["cpu_info"]),
        'disk_info': bool(config["Settings"]["disk_info"]),
        'listening_sockets': bool(config["Settings"]["listening_sockets"]),
        'tcp_connection_states': bool(config["Settings"]["tcp_connection_states"]),
        'network_info': bool(config["Settings"]["network_info"]),
    }
    return settings
