import grpc
import asyncio
from concurrent import futures
from collections import deque, defaultdict
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)
import daemon_sysmon_pb2
import daemon_sysmon_pb2_grpc
import logging
import time


def average_listening_sockets(stats_list):
    unique_sockets = {}

    # Суммируем уникальные сокеты
    for stats in stats_list:
        for net_info in stats.listening_sockets:
            socket_key = (net_info.command, net_info.pid, net_info.protocol, net_info.port)
            if socket_key not in unique_sockets:
                unique_sockets[socket_key] = daemon_sysmon_pb2.NetworkInfo(
                    command=net_info.command,
                    pid=net_info.pid,
                    user=net_info.user,
                    protocol=net_info.protocol,
                    port=net_info.port
                )

    return list(unique_sockets.values())


def average_tcp_states(stats_list):
    tcp_totals = {
        "estab": 0,
        "fin_wait": 0,
        "syn_rcv": 0,
        "time_wait": 0,
        "close_wait": 0,
        "last_ack": 0,
        "listen": 0,
        "close": 0,
        "unknown": 0
    }

    for stats in stats_list:
        tcp_totals["estab"] += stats.tcp_states.estab
        tcp_totals["fin_wait"] += stats.tcp_states.fin_wait
        tcp_totals["syn_rcv"] += stats.tcp_states.syn_rcv
        tcp_totals["time_wait"] += stats.tcp_states.time_wait
        tcp_totals["close_wait"] += stats.tcp_states.close_wait
        tcp_totals["last_ack"] += stats.tcp_states.last_ack
        tcp_totals["listen"] += stats.tcp_states.listen
        tcp_totals["close"] += stats.tcp_states.close
        tcp_totals["unknown"] += stats.tcp_states.unknown

    n = len(stats_list)
    tcp_averages = {
        "estab": tcp_totals["estab"] // n,
        "fin_wait": tcp_totals["fin_wait"] // n,
        "syn_rcv": tcp_totals["syn_rcv"] // n,
        "time_wait": tcp_totals["time_wait"] // n,
        "close_wait": tcp_totals["close_wait"] // n,
        "last_ack": tcp_totals["last_ack"] // n,
        "listen": tcp_totals["listen"] // n,
        "close": tcp_totals["close"] // n,
        "unknown": tcp_totals["unknown"] // n
    }

    return tcp_averages


def average_cpu_info(stats_list):
    cpu_totals = {
        "user_mode": 0.0,
        "system_mode": 0.0,
        "idle_mode": 0.0,
        "load_avg_min": 0.0,
        "load_avg_5min": 0.0,
        "load_avg_15min": 0.0
    }

    for stats in stats_list:
        cpu_totals["user_mode"] += stats.cpu.user_mode
        cpu_totals["system_mode"] += stats.cpu.system_mode
        cpu_totals["idle_mode"] += stats.cpu.idle_mode
        cpu_totals["load_avg_min"] += stats.cpu.load_avg_min
        cpu_totals["load_avg_5min"] += stats.cpu.load_avg_5min
        cpu_totals["load_avg_15min"] += stats.cpu.load_avg_15min

    n = len(stats_list)
    cpu_averages = {
        "user_mode": cpu_totals["user_mode"] / n,
        "system_mode": cpu_totals["system_mode"] / n,
        "idle_mode": cpu_totals["idle_mode"] / n,
        "load_avg_min": cpu_totals["load_avg_min"] / n,
        "load_avg_5min": cpu_totals["load_avg_5min"] / n,
        "load_avg_15min": cpu_totals["load_avg_15min"] / n
    }

    return cpu_averages


def average_device_info(stats_list):
    device_totals = defaultdict(lambda: {
        "tps": 0.0,
        "kb_read_per_s": 0.0,
        "kb_write_per_s": 0.0,
        "count": 0
    })

    for stats in stats_list:
        for dev_info in stats.devices:
            device_totals[dev_info.device]["tps"] += dev_info.tps
            device_totals[dev_info.device]["kb_read_per_s"] += dev_info.kb_read_per_s
            device_totals[dev_info.device]["kb_write_per_s"] += dev_info.kb_write_per_s
            device_totals[dev_info.device]["count"] += 1

    dev_averages = []
    for device, totals in device_totals.items():
        count = totals["count"]
        dev_averages.append(daemon_sysmon_pb2.DeviceStats(
            device=device,
            tps=totals["tps"] / count,
            kb_read_per_s=totals["kb_read_per_s"] / count,
            kb_write_per_s=totals["kb_write_per_s"] / count
        ))

    return dev_averages


def average_filesystems(stats_list):
    fs_totals = defaultdict(lambda: {
        "inodes": 0,
        "iused": 0,
        "iuse_calculated_percent": 0.0,
        "used_mb": 0.0,
        "space_used_percent": 0.0,
        "count": 0
    })

    # Суммируем данные для каждой уникальной файловой системы
    for stats in stats_list:
        for fs_info in stats.filesystems:
            fs_key = (fs_info.filesystem, fs_info.inodes,
                      fs_info.iused)  # Уникальный ключ на основе файловой системы и её данных
            fs_totals[fs_key]["inodes"] += fs_info.inodes
            fs_totals[fs_key]["iused"] += fs_info.iused
            fs_totals[fs_key]["iuse_calculated_percent"] += fs_info.iuse_calculated_percent
            fs_totals[fs_key]["used_mb"] += fs_info.used_mb
            fs_totals[fs_key]["space_used_percent"] += float(fs_info.space_used_percent)
            fs_totals[fs_key]["count"] += 1

    # Усредняем значения
    fs_averages = []
    for fs_key, totals in fs_totals.items():
        filesystem, inodes, iused = fs_key
        count = totals["count"]
        fs_averages.append(daemon_sysmon_pb2.FilesystemInfo(
            filesystem=filesystem,
            inodes=totals["inodes"] // count,  # Целочисленное деление
            iused=totals["iused"] // count,  # Целочисленное деление
            iuse_calculated_percent=totals["iuse_calculated_percent"] / count,
            used_mb=totals["used_mb"] / count,
            space_used_percent=totals["space_used_percent"] / count
        ))

    return fs_averages


def average_stats(stats_list):
    fs_averages = average_filesystems(stats_list)
    tcp_averages = average_tcp_states(stats_list)
    cpu_averages = average_cpu_info(stats_list)
    dev_averages = average_device_info(stats_list)
    unique_sockets = average_listening_sockets(stats_list)

    return daemon_sysmon_pb2.SystemStats(
        filesystems=fs_averages,
        cpu=daemon_sysmon_pb2.CpuInfo(**cpu_averages),
        devices=dev_averages,
        listening_sockets=unique_sockets,
        tcp_states=daemon_sysmon_pb2.TcpConnectionStates(**tcp_averages)
    )


class SystemMonitor(daemon_sysmon_pb2_grpc.SystemInfoServiceServicer):
    def __init__(self):
        self.stats_history = deque()
        self.lock = asyncio.Lock()
        self.collect_data_period = 1
        self.collect_data_task = None  # Хранить задачу сбора данных

    async def collect_data(self):
        while True:
            logging.info("Начинаем сбор данных")
            await asyncio.sleep(self.collect_data_period)
            filesystem_info = await get_fs_info()
            cpu_info = await get_top_info()
            disk_info = await get_disk_load()
            listening_sockets = await get_listening_sockets()
            tcp_connection_states = await get_tcp_connection_states()
            logging.info("Собрали данные")

            fs_info = [
                daemon_sysmon_pb2.FilesystemInfo(
                    filesystem=fs['Filesystem'],
                    inodes=fs['Inodes'],
                    iused=fs['IUsed'],
                    iuse_calculated_percent=fs['IUse Calculated%'],
                    used_mb=fs['Used MB'],
                    space_used_percent=fs['Space Used%']
                ) for fs in filesystem_info
            ]
            cpu = daemon_sysmon_pb2.CpuInfo(
                user_mode=cpu_info['user_mode'],
                system_mode=cpu_info['system_mode'],
                idle_mode=cpu_info['idle_mode'],
                load_avg_min=cpu_info['load_avg_min'],
                load_avg_5min=cpu_info['load_avg_5min'],
                load_avg_15min=cpu_info['load_avg_15min']
            )

            dev_stats = [
                daemon_sysmon_pb2.DeviceStats(
                    device=dev['Device'],
                    tps=dev['tps'],
                    kb_read_per_s=dev['kB_read/s'],
                    kb_write_per_s=dev['kB_write/s']
                ) for dev in disk_info
            ]

            net_info = [
                daemon_sysmon_pb2.NetworkInfo(
                    command=net['Command'],
                    pid=net['PID'],
                    user=net['User'],
                    protocol=net['Protocol'],
                    port=net['Port']
                ) for net in listening_sockets
            ]

            tcp_states = daemon_sysmon_pb2.TcpConnectionStates(
                estab=int(tcp_connection_states['ESTAB']),
                fin_wait=int(tcp_connection_states['FIN_WAIT']),
                syn_rcv=int(tcp_connection_states['SYN_RCV']),
                time_wait=int(tcp_connection_states['TIME-WAIT']),
                close_wait=int(tcp_connection_states['CLOSE-WAIT']),
                last_ack=int(tcp_connection_states['LAST-ACK']),
                listen=int(tcp_connection_states['LISTEN']),
                close=int(tcp_connection_states['CLOSE']),
                unknown=int(tcp_connection_states['UNKNOWN'])
            )
            async with self.lock:
                self.stats_history.append(
                    daemon_sysmon_pb2.SystemStats(
                        filesystems=fs_info,
                        cpu=cpu,
                        devices=dev_stats,
                        listening_sockets=net_info,
                        tcp_states=tcp_states
                    )
                )
                logging.info("Добавили данные в историю")

                # Оставляем только последние M секунд данных
                if len(self.stats_history) > 60:
                    self.stats_history.popleft()

    async def GetSystemStats(self, request, context):
        interval = request.interval
        window = request.window
        logging.info(f"Получен запрос от клиента с интервалом {interval} и окном {window}")

        # Запускаем сбор данных в фоновом режиме
        if self.collect_data_task is None or self.collect_data_task.done():
            self.collect_data_task = asyncio.create_task(self.collect_data())

        # Сначала ждем, пока накопится достаточно данных
        while len(self.stats_history) <= window / self.collect_data_period:
            await asyncio.sleep(self.collect_data_period)

        while True:
            async with self.lock:
                # Получаем данные за последние M секунд
                stats_list = list(self.stats_history)[-window:]
                logging.info(f"Получаем статистику для окна {window} секунд")

            if stats_list:
                # Усреднение данных
                averaged_stats = average_stats(stats_list)
                yield averaged_stats

            await asyncio.sleep(interval)


async def serve():
    system_monitor = SystemMonitor()
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    daemon_sysmon_pb2_grpc.add_SystemInfoServiceServicer_to_server(system_monitor, server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    print("Server started on port 50051")
    # Ожидаем завершения сервера
    await server.wait_for_termination()
