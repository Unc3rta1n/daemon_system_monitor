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
    config.read("config.ini")
    return config


def configure_daemon():
    config = get_config()
    settings = {
        'filesystem_info': config.getboolean("Settings", "filesystem_info"),
        'cpu_info': config.getboolean("Settings", "cpu_info"),
        'disk_info': config.getboolean("Settings", "disk_info"),
        'listening_sockets': config.getboolean("Settings", "listening_sockets"),
        'tcp_connection_states': config.getboolean("Settings", "tcp_connection_states"),
        'network_info': config.getboolean("Settings", "network_info"),
    }
    return settings
