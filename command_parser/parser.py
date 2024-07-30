import asyncio
import re
import logging
from datetime import datetime, timedelta

PROTO_PATTERN = re.compile(r':\s(\w+)')
IP_PATTERN = re.compile(r'(\S+)\s>\s(\S+):')
IPv4_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d+)')
IPv6_PATTERN = re.compile(r'([0-9a-fA-F:]+)\.(\d+)')


async def get_fs_info():
    # Получаем информацию о inode
    inode_info = await asyncio.create_subprocess_shell(
        'df -i',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await inode_info.communicate()
    inode = stdout.decode().strip().split('\n')

    # Получаем информацию о размере
    size_info = await asyncio.create_subprocess_shell(
        'df -k',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await size_info.communicate()
    size = stdout.decode().strip().split('\n')

    size_dict = {}
    for line in size:
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            filesystem = parts[0]
            total_kb = int(parts[1])
            used_kb = int(parts[2])
            available_kb = int(parts[3])
        except ValueError:
            continue

        if total_kb > 0:
            space_used_percent = (used_kb / total_kb) * 100
        else:
            space_used_percent = 0

        size_dict[filesystem] = {
            'Total KB': total_kb,
            'Used KB': used_kb,
            'Available KB': available_kb,
            'Space Used%': space_used_percent
        }

    results = []
    for line in inode:
        parts = line.split()
        if len(parts) < 6:
            continue
        filesystem = parts[0]
        try:
            inodes = int(parts[1])
            iused = int(parts[2])
        except ValueError:
            continue

        if inodes <= 0 or iused < 0:
            iuse_calculated_percent = 0.0
        else:
            iuse_calculated_percent = (iused / inodes) * 100

        size_info = size_dict.get(filesystem, {})
        used_mb = size_info.get('Used KB', 0) / 1024
        space_used_percent = size_info.get('Space Used%', '0')

        results.append({
            'Filesystem': filesystem,
            'Inodes': inodes,
            'IUsed': iused,
            'IUse Calculated%': iuse_calculated_percent,
            'Used MB': used_mb,
            'Space Used%': space_used_percent
        })

    return results


async def get_disk_load():
    iostat_info = await asyncio.create_subprocess_shell(
        'iostat -d -k',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await iostat_info.communicate()
    iostat = stdout.decode().strip().split('\n')
    result = []
    for line in iostat[3:]:
        parts = line.split()
        disk_dict = {'Device': parts[0],
                     'tps': float(parts[1]),
                     'kB_read/s': float(parts[2]),
                     'kB_write/s': float(parts[3])}
        result.append(disk_dict)

    return result


async def get_top_info():
    stdout = await asyncio.create_subprocess_shell(
        'top -b -n1',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    output, _ = await stdout.communicate()
    lines = output.decode().strip().split('\n')
    line = lines[0]
    _line = lines[2]
    pattern = r'(\d+\.\d+)\s+us,\s+(\d+\.\d+)\s+sy,.*?(\d+\.\d+)\s+id'

    match = re.search(pattern, _line)
    if match:
        us_value = float(match.group(1))
        sy_value = float(match.group(2))
        id_value = float(match.group(3))
    else:
        us_value = 0
        sy_value = 0
        id_value = 0
    pattern = r'load average: (\d+\.\d+), (\d+\.\d+), (\d+\.\d+)'
    match = re.search(pattern, line)

    if match:
        load_avg_1 = float(match.group(1))
        load_avg_5 = float(match.group(2))
        load_avg_15 = float(match.group(3))
    else:
        load_avg_1 = 0
        load_avg_5 = 0
        load_avg_15 = 0

    result = {'user_mode': us_value,
              'system_mode': sy_value,
              'idle_mode': id_value,
              'load_avg_min': load_avg_1,
              'load_avg_5min': load_avg_5,
              'load_avg_15min': load_avg_15,
              }
    return result


async def get_listening_sockets():
    sudo_pass = 'ZaqZaq12e'
    result = await asyncio.create_subprocess_shell(
        f'echo {sudo_pass} | sudo -S netstat -lntup',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    output, _ = await result.communicate()

    lines = output.decode().splitlines()
    sockets_info = []

    for line in lines[2:]:
        parts = re.split(r'\s+', line)
        if len(parts) < 7:
            continue

        protocol = parts[0]
        port = parts[3].split(':')[-1]
        pid_command = parts[6].split('/')
        pid = pid_command[0]
        command = pid_command[1] if len(pid_command) > 1 else 'N/A'
        user = 'N/A'
        sockets_info.append({
            'Command': command,
            'PID': pid,
            'User': user,
            'Protocol': protocol,
            'Port': port
        })

    return sockets_info


async def get_tcp_connection_states():
    result = await asyncio.create_subprocess_shell(
        'ss -ta',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    output, _ = await result.communicate()

    lines = output.decode().splitlines()
    states_count = {
        'ESTAB': 0,
        'FIN_WAIT': 0,
        'SYN_RCV': 0,
        'TIME-WAIT': 0,
        'CLOSE-WAIT': 0,
        'LAST-ACK': 0,
        'LISTEN': 0,
        'CLOSE': 0,
        'UNKNOWN': 0
    }

    for line in lines[1:]:
        parts = re.split(r'\s+', line)
        if len(parts) < 1:
            continue

        state = parts[0]
        if state in states_count:
            states_count[state] += 1
        else:
            states_count['UNKNOWN'] += 1

    return states_count


async def capture_traffic():
    sudo_pass = 'ZaqZaq12e'
    process = await asyncio.create_subprocess_shell(
        f'echo {sudo_pass} | sudo -S tcpdump -i any -Q inout -l -q -n',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process


async def parse_tcpdump_output(reader, duration):
    protocol_data = {}  # {protocol: total_bytes}
    traffic_data = {}  # {(src_ip, src_port, dst_ip, dst_port, protocol): {'bytes': 0}}

    end_time = datetime.now() + timedelta(seconds=duration)
    logging.info("Начало захвата трафика")

    while datetime.now() < end_time:
        try:
            # Устанавливаем тайм-аут для ожидания данных
            line = await asyncio.wait_for(reader.readline(), 0.10)

            if not line:
                logging.info('Поток завершился или нет данных')
                break

            line = line.decode('utf-8').strip()

            try:
                addr = []
                # logging.info(f'да, строка пришла {line}')
                match = IP_PATTERN.search(line)
                if match:
                    addr.append(match.group(1))
                    addr.append(match.group(2))
                else:
                    continue

                match = PROTO_PATTERN.search(line)
                if match:
                    protocol = match.group(1)
                else:
                    continue
                src_ip, src_port, dst_ip, dst_port = addr[0], 0, addr[1], 0
                if protocol != 'ICMP':
                    ipv4_match = IPv4_PATTERN.search(addr[0])
                    ipv6_match = IPv6_PATTERN.search(addr[0])

                    if ipv4_match:
                        src_ip = ipv4_match.group(1)
                        src_port = ipv4_match.group(2)
                    elif ipv6_match:
                        src_ip = ipv6_match.group(1)
                        src_port = ipv6_match.group(2)

                    ipv4_match = IPv4_PATTERN.search(addr[1])
                    ipv6_match = IPv6_PATTERN.search(addr[1])

                    if ipv4_match:
                        dst_ip = ipv4_match.group(1)
                        dst_port = ipv4_match.group(2)
                    elif ipv6_match:
                        dst_ip = ipv6_match.group(1)
                        dst_port = ipv6_match.group(2)

                line = line.split()
                length = int(line[-1])

                # Обновление данных по протоколу
                if protocol not in protocol_data:
                    protocol_data[protocol] = 0
                protocol_data[protocol] += length

                if src_ip == src_port or dst_ip == dst_port:
                    logging.info(f"алярм {addr[0]}, {addr[1]}")
                # Обновление данных по трафику
                flow_key = (src_ip, src_port, dst_ip, dst_port, protocol)
                if flow_key not in traffic_data:
                    traffic_data[flow_key] = {'bytes': 0}
                traffic_data[flow_key]['bytes'] += length
            except Exception as e:
                logging.error(e)
                continue

        except asyncio.TimeoutError:
            pass
            # logging.warning('Тайм-аут ожидания данных, продолжаем цикл')

    logging.info("Завершение захвата трафика")
    return protocol_data, traffic_data
