import asyncio
import subprocess
import re


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
            'Space Used%': f"{space_used_percent:.2f}%"
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
            ifree = int(parts[3])
            iuse_percent = parts[4]
            mount_point = parts[5]
        except ValueError:
            continue

        if inodes <= 0 or iused < 0:
            iuse_calculated_percent = 'Invalid data'
        else:
            iuse_calculated_percent = (iused / inodes) * 100

        size_info = size_dict.get(filesystem, {})
        used_mb = size_info.get('Used KB', 0) / 1024
        space_used_percent = size_info.get('Space Used%', '0%')

        results.append({
            'Filesystem': filesystem,
            'Inodes': inodes,
            'IUsed': iused,
            'IUse Calculated%': f"{iuse_calculated_percent:.2f}%" if isinstance(iuse_calculated_percent, float)
            else iuse_calculated_percent,
            'Used MB': f"{used_mb:.2f}",
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
                     'tps': parts[1],
                     'kB_read/s': parts[2],
                     'kB_write/s': parts[3]}
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
    line = [word for segment in lines[0].split(',') for word in segment.split()]
    _line = [word for segment in lines[2].split(',') for word in segment.split()]
    result = {'user_mode': _line[1],
              'system_mode': _line[3],
              'idle_mode': _line[7],
              'load_avg_min': line[9],
              'load_avg_5min': line[10],
              'load_avg_15min': line[11]
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
