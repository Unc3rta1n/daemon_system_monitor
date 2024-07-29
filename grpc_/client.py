import grpc
import asyncio
import datetime
from tabulate import tabulate
import daemon_sysmon_pb2
import daemon_sysmon_pb2_grpc
import argparse


async def get_system_stats(stub, interval: int, window: int):
    # Создаем запрос с указанными интервалом и окном
    request = daemon_sysmon_pb2.SystemStatsRequest(interval=interval, window=window)

    try:
        # Используем асинхронный gRPC вызов для получения системных статов
        async for response in stub.GetSystemStats(request):
            print(f"Timestamp: {datetime.datetime.now()}\n")
            print_system_stats(response)
            print("\n" + "=" * 50 + "\n")
    except grpc.RpcError as e:
        print(f"gRPC error: {e}")


def print_system_stats(stats):
    # Filesystem Info
    fs_headers = ["Filesystem", "Inodes", "IUsed", "IUse Calculated%", "Used MB", "Space Used%"]
    fs_table = [
        [
            fs.filesystem,
            fs.inodes,
            fs.iused,
            fs.iuse_calculated_percent,
            fs.used_mb,
            fs.space_used_percent
        ]
        for fs in stats.filesystems
    ]
    print("Filesystem Info:")
    print(tabulate(fs_table, headers=fs_headers, tablefmt="grid"))

    # CPU Info
    cpu_headers = ["User Mode", "System Mode", "Idle Mode", "Load Avg 1min", "Load Avg 5min", "Load Avg 15min"]
    cpu_table = [[
        stats.cpu.user_mode,
        stats.cpu.system_mode,
        stats.cpu.idle_mode,
        stats.cpu.load_avg_min,
        stats.cpu.load_avg_5min,
        stats.cpu.load_avg_15min
    ]]
    print("\nCPU Info:")
    print(tabulate(cpu_table, headers=cpu_headers, tablefmt="grid"))

    # Device Stats
    device_headers = ["Device", "TPS", "kB_read/s", "kB_write/s"]
    device_table = [
        [
            device.device,
            device.tps,
            device.kb_read_per_s,
            device.kb_write_per_s
        ]
        for device in stats.devices
    ]
    print("\nDevice Stats:")
    print(tabulate(device_table, headers=device_headers, tablefmt="grid"))

    # Listening Sockets
    socket_headers = ["Command", "PID", "User", "Protocol", "Port"]
    socket_table = [
        [
            socket.command,
            socket.pid,
            socket.user,
            socket.protocol,
            socket.port
        ]
        for socket in stats.listening_sockets
    ]
    print("\nListening Sockets:")
    print(tabulate(socket_table, headers=socket_headers, tablefmt="grid"))

    # TCP Connection States
    tcp_headers = ["State", "Count"]
    tcp_table = [
        ["ESTAB", stats.tcp_states.estab],
        ["FIN_WAIT", stats.tcp_states.fin_wait],
        ["SYN_RCV", stats.tcp_states.syn_rcv],
        ["TIME-WAIT", stats.tcp_states.time_wait],
        ["CLOSE-WAIT", stats.tcp_states.close_wait],
        ["LAST-ACK", stats.tcp_states.last_ack],
        ["LISTEN", stats.tcp_states.listen],
        ["CLOSE", stats.tcp_states.close],
        ["UNKNOWN", stats.tcp_states.unknown]
    ]
    print("\nTCP Connection States:")
    print(tabulate(tcp_table, headers=tcp_headers, tablefmt="grid"))

    # Top Talkers Protocol Stats
    proto_headers = ["Protocol", "bytes", "percent"]
    proto_table = [
        [
            proto.protocol,
            proto.bytes,
            proto.percent,
        ]
        for proto in stats.top_talkers_protocol
    ]
    print("\nProto Stats:")
    print(tabulate(proto_table, headers=proto_headers, tablefmt="grid"))

    # Top Talkers Traffic Stats
    traff_headers = ["src ip", "dst ip", "bytes"]
    traff_table = [
        [
            proto.src_ip,
            proto.dst_ip,
            proto.bytes,
        ]
        for proto in stats.top_talkers_traffic
    ]
    print("\nTraffic Stats:")
    print(tabulate(traff_table, headers=traff_headers, tablefmt="grid"))


async def run_client(port):
    # Подключаемся к gRPC серверу
    async with grpc.aio.insecure_channel(f'localhost:{port}') as channel:
        stub = daemon_sysmon_pb2_grpc.SystemInfoServiceStub(channel)
        await get_system_stats(stub, interval=5, window=15)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Клиент Системный монитор")
    parser.add_argument("port", type=int, help="Порт, где находится демон")
    args = parser.parse_args()

    asyncio.run(run_client(port=args.port))
