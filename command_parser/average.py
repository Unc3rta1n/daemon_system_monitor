from collections import defaultdict

import daemon_sysmon_pb2


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


def average_protocol(stats_list):
    protocol_totals = {}
    total_bytes = 0
    for stat in stats_list:
        for protocol_info in stat.top_talkers_protocol:
            protocol = protocol_info.protocol
            if protocol not in protocol_totals:
                protocol_totals[protocol] = 0
            protocol_totals[protocol] += protocol_info.bytes
            total_bytes += protocol_info.bytes

    prot_avg = []
    for key, value in protocol_totals.items():
        prot_avg.append(daemon_sysmon_pb2.TopTalkersProtocol(
            protocol=key,
            bytes=value,
            percent=value / total_bytes * 100
        ))

    # Сортировка по убыванию процента
    sorted_prot_avg = sorted(prot_avg, key=lambda x: x.percent, reverse=True)

    return sorted_prot_avg


def average_traffic(stats_list):
    traffic_totals = {}
    total_bytes = 0
    for stat in stats_list:
        for key, value in traffic_totals.items():
            if key not in traffic_totals:
                traffic_totals[key] = 0
            traffic_totals[key] += value


def average_stats(stats_list):
    fs_averages = average_filesystems(stats_list)
    tcp_averages = average_tcp_states(stats_list)
    cpu_averages = average_cpu_info(stats_list)
    dev_averages = average_device_info(stats_list)
    unique_sockets = average_listening_sockets(stats_list)
    protocol_averages = average_protocol(stats_list)

    return daemon_sysmon_pb2.SystemStats(
        filesystems=fs_averages,
        cpu=daemon_sysmon_pb2.CpuInfo(**cpu_averages),
        devices=dev_averages,
        listening_sockets=unique_sockets,
        tcp_states=daemon_sysmon_pb2.TcpConnectionStates(**tcp_averages),
        top_talkers_protocol=protocol_averages
    )
