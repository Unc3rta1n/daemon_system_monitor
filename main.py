import asyncio
import logging
import argparse
import configparser
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)
from grpc_.server import serve
from utils.utils import parse_args, init_logging, get_config

if __name__ == "__main__":
    args = parse_args()
    init_logging()
    config = get_config()

    if args.port:
        asyncio.run(serve(port=args.port))
    else:
        asyncio.run(serve())
