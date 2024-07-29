import asyncio
import logging
import argparse
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)
from grpc_.server import serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Демон Системный монитор")
    parser.add_argument("-port", type=int, help="Порт, на котором хотите развернуть демона")

    args = parser.parse_args()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console_handler])

    if args.port:
        asyncio.run(serve(port=args.port))
    else:
        asyncio.run(serve())
