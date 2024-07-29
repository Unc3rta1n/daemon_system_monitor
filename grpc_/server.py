import grpc
import asyncio
from concurrent import futures
from collections import deque, defaultdict
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states, capture_traffic, parse_tcpdump_output)
from command_parser.average import (average_listening_sockets, average_stats, average_filesystems,
                                    average_tcp_states, average_cpu_info, average_device_info)
import daemon_sysmon_pb2
import daemon_sysmon_pb2_grpc
import logging


class SystemMonitor(daemon_sysmon_pb2_grpc.SystemInfoServiceServicer):
    def __init__(self):
        self.stats_history = deque()
        self.lock = asyncio.Lock()
        self.collect_data_period = 1
        self.collect_data_task = None  # Хранить задачу сбора данных

    async def collect_data(self):
        process = await capture_traffic(self.collect_data_period)
        while True:
            logging.info("Начинаем сбор данных")
            filesystem_info = await get_fs_info()
            cpu_info = await get_top_info()
            disk_info = await get_disk_load()
            listening_sockets = await get_listening_sockets()
            tcp_connection_states = await get_tcp_connection_states()
            protocol_data, traffic_data = await parse_tcpdump_output(process.stdout, self.collect_data_period)
            logging.info("Собрали данные")
            await asyncio.sleep(self.collect_data_period)

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
            prot_info = [
                daemon_sysmon_pb2.TopTalkersProtocol(
                    protocol=prot,
                    bytes=_bytes,
                    percent=0,
                ) for prot, _bytes in protocol_data.items()
            ]
            top_talkers_traffic_list = []
            for (src_ip, src_port, dst_ip, dst_port, protocol), data in traffic_data.items():
                # Создайте экземпляр TopTalkersTraffic и заполните его данными
                top_talker = daemon_sysmon_pb2.TopTalkersTraffic(
                    src_ip=str(src_ip),  # Преобразование в строку для случая с 0
                    src_port=str(src_port),
                    dst_ip=str(dst_ip),
                    dst_port=str(dst_port),
                    protocol=protocol,
                    bytes=data['bytes']
                )
                top_talkers_traffic_list.append(top_talker)
            async with self.lock:
                self.stats_history.append(
                    daemon_sysmon_pb2.SystemStats(
                        filesystems=fs_info,
                        cpu=cpu,
                        devices=dev_stats,
                        listening_sockets=net_info,
                        tcp_states=tcp_states,
                        top_talkers_protocol=prot_info,
                        top_talkers_traffic=top_talkers_traffic_list
                    )
                )
                logging.info("Добавили данные в историю")

                if len(self.stats_history) > 60:
                    self.stats_history.popleft()

    async def GetSystemStats(self, request, context):
        interval = request.interval
        window = request.window
        logging.info(f"Получен запрос от клиента с интервалом {interval} и окном {window}")
        self.collect_data_period = interval // 2
        if self.collect_data_task is None or self.collect_data_task.done():
            self.collect_data_task = asyncio.create_task(self.collect_data())

        # Сначала ждем, пока накопится достаточно данных
        await asyncio.sleep(window)
        # рабочая тема, но надо чуть по другому сделать
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
