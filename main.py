import asyncio

from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)


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


asyncio.run(main())
