import subprocess


def get_inodes_fs():
    stdout = subprocess.run(['df', '-i'], capture_output=True, text=True)
    lines = stdout.stdout.strip().split('\n')
    results = []

    for line in lines:
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
        # Вычисляем процент использования inodes
        if inodes > 0 and iused > 0:
            iuse_calculated_percent = (iused / inodes) * 100
        else:
            iuse_calculated_percent = 0

        results.append({
            'Filesystem': filesystem,
            'Inodes': inodes,
            'IUsed': iused,
            'IFree': ifree,
            'IUse%': iuse_percent,
            'IUse Calculated%': f"{iuse_calculated_percent:.2f}%",
            'Mounted on': mount_point
        })
    return results


def get_top_info():
    stdout = subprocess.run(['top', '-b', '-n1'], capture_output=True, text=True)
    lines = stdout.stdout.strip().split('\n')
    line = [word for segment in lines[0].split(',') for word in segment.split()]
    _line = [word for segment in lines[2].split(',') for word in segment.split()]
    # сплит по запятым, и по пробелам,
    # иначе там один параметр ломается и неудобно парсить
    user_mode = _line[1]
    system_mode = _line[3]
    idle = _line[7]
    load_avg_min = line[9]
    load_avg_5min = line[10]
    load_avg_15min = line[11]
    result = {'user_mode': user_mode,
              'system_mode': system_mode,
              'idle_mode': idle,
              'load_avg_min': load_avg_min,
              'load_avg_5min': load_avg_5min,
              'load_avg_15min': load_avg_15min
              }

    return result
