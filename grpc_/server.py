import grpc

import grpc_
import asyncio
from concurrent import futures
from collections import deque
from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)
import daemon_sysmon_pb2
import daemon_sysmon_pb2_grpc
import logging


class SystemMonitor(daemon_sysmon_pb2_grpc.SystemInfoServiceServicer):
    def __init__(self):
        self.stats_history = deque()
        self.lock = asyncio.Lock()
        self.collect_data_period = 1

    async def collect_data(self):
        while True:
            logging.info("курим")
            await asyncio.sleep(self.collect_data_period)
            logging.info("не курим")

            filesystem_info = await get_fs_info()
            cpu_info = await get_top_info()
            disk_info = await get_disk_load()
            listening_sockets = await get_listening_sockets()
            tcp_connection_states = await get_tcp_connection_states()
            logging.info("собрали инфу")

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
                estab=tcp_connection_states['ESTAB'],
                fin_wait=tcp_connection_states['FIN_WAIT'],
                syn_rcv=tcp_connection_states['SYN_RCV'],
                time_wait=tcp_connection_states['TIME-WAIT'],
                close_wait=tcp_connection_states['CLOSE-WAIT'],
                last_ack=tcp_connection_states['LAST-ACK'],
                listen=tcp_connection_states['LISTEN'],
                close=tcp_connection_states['CLOSE'],
                unknown=tcp_connection_states['UNKNOWN']
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
                logging.info("заапендили")

                if len(self.stats_history) > 60:  # Храним историю за последние 60 секунд
                    self.stats_history.popleft()

    async def GetSystemStats(self, request, context):
        interval = request.interval
        window = request.window
        logging.info("пришел запрос от клиента")

        await asyncio.sleep(window)  # Ожидание перед первым выводом

        while True:
            async with self.lock:
                stats_list = list(self.stats_history)[-window:]
                logging.info("смотрим статс лист")

            if not stats_list:
                logging.info("бля, пустой")
                continue

            # Усреднение данных
            averaged_stats = self.average_stats(stats_list)
            yield averaged_stats

            await asyncio.sleep(interval)

    def average_stats(self, stats_list):
        fs_info_averages = []
        cpu_info_average = {
            "user_mode": 0,
            "system_mode": 0,
            "idle_mode": 0,
            "load_avg_min": 0,
            "load_avg_5min": 0,
            "load_avg_15min": 0
        }
        dev_stats_averages = []
        tcp_states_average = {
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

        n = len(stats_list)

        for stats in stats_list:
            # Усредняем данные о файловых системах
            for fs_info in stats.filesystems:
                matched_fs = next((fs for fs in fs_info_averages if fs.filesystem == fs_info.filesystem), None)
                if not matched_fs:
                    fs_info_averages.append(
                        daemon_sysmon_pb2.FilesystemInfo(
                            filesystem=fs_info.filesystem,
                            inodes=fs_info.inodes / n,
                            iused=fs_info.iused / n,
                            iuse_calculated_percent=fs_info.iuse_calculated_percent / n,
                            used_mb=fs_info.used_mb / n,
                            space_used_percent=float(fs_info.space_used_percent.strip('%')) / n
                        )
                    )
                else:
                    matched_fs.inodes += fs_info.inodes / n
                    matched_fs.iused += fs_info.iused / n
                    matched_fs.iuse_calculated_percent += fs_info.iuse_calculated_percent / n
                    matched_fs.used_mb += fs_info.used_mb / n
                    matched_fs.space_used_percent += float(fs_info.space_used_percent.strip('%')) / n

            # Усредняем данные о CPU
            cpu_info_average['user_mode'] += float(stats.cpu.user_mode.strip('%')) / n
            cpu_info_average['system_mode'] += float(stats.cpu.system_mode.strip('%')) / n
            cpu_info_average['idle_mode'] += float(stats.cpu.idle_mode.strip('%')) / n
            cpu_info_average['load_avg_min'] += float(stats.cpu.load_avg_min) / n
            cpu_info_average['load_avg_5min'] += float(stats.cpu.load_avg_5min) / n
            cpu_info_average['load_avg_15min'] += float(stats.cpu.load_avg_15min) / n

            # Усредняем данные об устройствах
            for dev_info in stats.devices:
                matched_dev = next((dev for dev in dev_stats_averages if dev.device == dev_info.device), None)
                if not matched_dev:
                    dev_stats_averages.append(
                        daemon_sysmon_pb2.DeviceStats(
                            device=dev_info.device,
                            tps=float(dev_info.tps) / n,
                            kb_read_per_s=float(dev_info.kb_read_per_s) / n,
                            kb_write_per_s=float(dev_info.kb_write_per_s) / n
                        )
                    )
                else:
                    matched_dev.tps += float(dev_info.tps) / n
                    matched_dev.kb_read_per_s += float(dev_info.kb_read_per_s) / n
                    matched_dev.kb_write_per_s += float(dev_info.kb_write_per_s) / n

            # Усредняем данные о состояниях TCP
            tcp_states_average['estab'] += stats.tcp_states.estab / n
            tcp_states_average['fin_wait'] += stats.tcp_states.fin_wait / n
            tcp_states_average['syn_rcv'] += stats.tcp_states.syn_rcv / n
            tcp_states_average['time_wait'] += stats.tcp_states.time_wait / n
            tcp_states_average['close_wait'] += stats.tcp_states.close_wait / n
            tcp_states_average['last_ack'] += stats.tcp_states.last_ack / n
            tcp_states_average['listen'] += stats.tcp_states.listen / n
            tcp_states_average['close'] += stats.tcp_states.close / n
            tcp_states_average['unknown'] += stats.tcp_states.unknown / n

        cpu_info = daemon_sysmon_pb2.CpuInfo(
            user_mode=f"{cpu_info_average['user_mode']:.2f}%",
            system_mode=f"{cpu_info_average['system_mode']:.2f}%",
            idle_mode=f"{cpu_info_average['idle_mode']:.2f}%",
            load_avg_min=f"{cpu_info_average['load_avg_min']:.2f}",
            load_avg_5min=f"{cpu_info_average['load_avg_5min']:.2f}",
            load_avg_15min=f"{cpu_info_average['load_avg_15min']:.2f}"
        )

        tcp_states = daemon_sysmon_pb2.TcpConnectionStates(
            estab=int(tcp_states_average['estab']),
            fin_wait=int(tcp_states_average['fin_wait']),
            syn_rcv=int(tcp_states_average['syn_rcv']),
            time_wait=int(tcp_states_average['time_wait']),
            close_wait=int(tcp_states_average['close_wait']),
            last_ack=int(tcp_states_average['last_ack']),
            listen=int(tcp_states_average['listen']),
            close=int(tcp_states_average['close']),
            unknown=int(tcp_states_average['unknown'])
        )

        return daemon_sysmon_pb2.SystemStats(
            filesystems=fs_info_averages,
            cpu=cpu_info,
            devices=dev_stats_averages,
            tcp_states=tcp_states
        )


async def serve():
    system_monitor = SystemMonitor()
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    daemon_sysmon_pb2_grpc.add_SystemInfoServiceServicer_to_server(system_monitor, server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    print("Server started on port 50051")
    # Запускаем сбор данных в фоновом режиме
    collect_data_task = asyncio.create_task(system_monitor.collect_data())

    # Ожидаем завершения сервера
    await server.wait_for_termination()

    # Отменяем задачу сбора данных при завершении сервера
    collect_data_task.cancel()

    await server.wait_for_termination()
