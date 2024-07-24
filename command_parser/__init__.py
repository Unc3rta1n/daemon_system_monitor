import subprocess
import re


def parse_tcpdump_line(line):
    """
    Обработать строку вывода tcpdump и извлечь интересующую информацию.
    """
    # Пример использования регулярного выражения для парсинга строки
    # Формат строки может быть разным, адаптируйте регулярное выражение под ваш вывод tcpdump

    pattern = re.compile(
        r"(?P<date>\d{4}-\d{2}-\d{2})\s+"  # Дата
        r"(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+"  # Время
        r"(?P<interface>\S+)\s+"  # Интерфейс
        r"(?P<direction>In|Out)\s+"  # Направление
        r"IP\s+"
        r"(?P<src_ip>[\d.]+)\.(?P<src_port>\d+)\s+>\s+"  # IP и порт источника
        r"(?P<dst_ip>[\d.]+)\.(?P<dst_port>\d+):\s+"  # IP и порт назначения
        r"Flags\s+\[(?P<flags>[^]]+)],\s+"  # Флаги
        r"ack\s+(?P<ack>\d+),\s+"  # Номер подтверждения
        r"win\s+(?P<win>\d+),\s+"  # Размер окна
        r"options\s+\[(?P<options>[^]]+)],\s+"  # Опции
        r"length\s+(?P<length>\d+)")

    # Поиск соответствий
    match = pattern.match(line)
    if match:
        data = match.groupdict()
        print("Parsed Data:")
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print("No match found")


def run_tcpdump():
    """
    Запустить tcpdump и обрабатывать вывод.
    """
    # Запуск команды tcpdump
    process = subprocess.Popen(
        ['tcpdump', '-nt', '-i', 'any', '-Q', 'inout', '-ttt', '-l'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        while True:
            # Чтение очередной строки вывода
            line = process.stdout.readline()
            if not line:
                break
            parse_tcpdump_line(line)

    except KeyboardInterrupt:
        print("Остановка программы.")
    finally:
        process.terminate()
        process.wait()


if __name__ == "__main__":
    run_tcpdump()
