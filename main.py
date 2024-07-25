import asyncio
import logging
import grpc

import daemon_sysmon_pb2_grpc
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)
from grpc_.server import serve


async def main():
    filesystem_info = await get_fs_info()
    cpu_info = await get_top_info()
    device_stats = await get_disk_load()
    listening_sockets = await get_listening_sockets()
    tcp_states = await get_tcp_connection_states()

    for line in filesystem_info:
        print(line)

    print(cpu_info)

    for line in device_stats:
        print(line)

    print("Listening Sockets:")
    for info in listening_sockets:
        print(info)

    print("\nTCP Connection States:")

    for state, count in tcp_states.items():
        print(f"{state}: {count}")


if __name__ == "__main__":
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[console_handler])

    asyncio.run(serve())
