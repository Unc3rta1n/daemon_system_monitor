import subprocess
import asyncio
from command_parser.parser import get_inodes_fs, get_top_info


res1 = get_inodes_fs()
for line in res1:
    print(line)
# stdout = subprocess.run(['top', '-b', '-n1'], capture_output=True, text=True)
# print(stdout.stdout)

res2 = get_top_info()

print(f"user mode {res2['user_mode']}")
print(f"system mode {res2['system_mode']}")
print(f"idle mode {res2['idle_mode']}")
print(f"load avg minute {res2['load_avg_min']}")
print(f"load avg 5minute {res2['load_avg_5min']}")
print(f"load avg 15minute {res2['load_avg_15min']}")
