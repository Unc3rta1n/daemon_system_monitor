import subprocess
import re


def get_fs_info():
    # Получаем информацию о inode
    inode_info = subprocess.run(['df', '-i'], capture_output=True, text=True)
    inode = inode_info.stdout.strip().split('\n')

    # Получаем информацию о размере
    size_info = subprocess.run(['df', '-k'], capture_output=True, text=True)
    size = size_info.stdout.strip().split('\n')

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
            # Пропускаем заголовки или некорректные данные
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
            # Пропускаем заголовки или некорректные данные
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
            'IFree': ifree,
            'IUse%': iuse_percent,
            'IUse Calculated%': f"{iuse_calculated_percent:.2f}%" if isinstance(iuse_calculated_percent, float)
            else iuse_calculated_percent,
            'Mounted on': mount_point,
            'Used MB': f"{used_mb:.2f}",
            'Space Used%': space_used_percent
        })

    return results


def get_disk_load():
    # Получаем информацию о загрузке диска(tps, kb_read/s...)
    iostat_info = subprocess.run(['iostat', '-d', '-k'], capture_output=True, text=True)
    iostat = iostat_info.stdout.strip().split('\n')
    result = []
    for line in iostat[3:]:
        parts = line.split()
        disk_dict = {'Device': parts[0],
                     'tps': parts[1],
                     'kB_read/s': parts[2],
                     'kB_write/s': parts[3]}
        result.append(disk_dict)

    return result


def get_top_info():
    stdout = subprocess.run(['top', '-b', '-n1'], capture_output=True, text=True)
    lines = stdout.stdout.strip().split('\n')
    line = [word for segment in lines[0].split(',') for word in segment.split()]
    _line = [word for segment in lines[2].split(',') for word in segment.split()]
    # сплит по запятым, и по пробелам,
    # иначе там один параметр ломается и неудобно парсить
    result = {'user_mode': _line[1],
              'system_mode': _line[3],
              'idle_mode': _line[7],
              'load_avg_min': line[9],
              'load_avg_5min': line[10],
              'load_avg_15min': line[11]
              }

    return result


def get_listening_sockets():
    sudo_pass = 'ZaqZaq12e'  # надо закинуть в конфиг
    # Выполняем команду для получения информации о слушающих сокетах
    result = subprocess.run(
        ['sudo', '-S', 'netstat', '-lntup'],
        input=sudo_pass + '\n',
        capture_output=True,
        text=True)

    output = result.stdout

    # Обрабатываем вывод команды
    lines = output.splitlines()
    sockets_info = []

    # Ищем строки, которые содержат информацию о сокетах
    for line in lines[2:]:  # Пропускаем первые две строки заголовков
        parts = re.split(r'\s+', line)
        if len(parts) < 7:
            continue

        protocol = parts[0]
        port = parts[3].split(':')[-1]
        pid_command = parts[6].split('/')
        pid = pid_command[0]
        command = pid_command[1] if len(pid_command) > 1 else 'N/A'
        user = 'N/A'  # В этом примере пользователь не извлекается
        sockets_info.append({
            'Command': command,
            'PID': pid,
            'User': user,
            'Protocol': protocol,
            'Port': port
        })

    return sockets_info


def get_tcp_connection_states():
    # Выполняем команду для получения информации о TCP соединениях
    result = subprocess.run(['ss', '-ta'], capture_output=True, text=True)
    output = result.stdout

    # Обрабатываем вывод команды
    lines = output.splitlines()
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

    # Ищем строки, которые содержат информацию о соединениях
    for line in lines[1:]:  # Пропускаем первую строку заголовков
        parts = re.split(r'\s+', line)
        if len(parts) < 1:
            continue

        state = parts[0]
        if state in states_count:
            states_count[state] += 1
        else:
            states_count['UNKNOWN'] += 1

    return states_count
