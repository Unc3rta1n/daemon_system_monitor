from command_parser.parser import (get_fs_info, get_top_info, get_disk_load, get_listening_sockets,
                                   get_tcp_connection_states)


res1 = get_fs_info()
for line in res1:
    print(line)

res2 = get_top_info()
print(res2)

res3 = get_disk_load()
for line in res3:
    print(line)

print("Listening Sockets:")
sockets_info = get_listening_sockets()
for info in sockets_info:
    print(info)

print("\nTCP Connection States:")
connection_states = get_tcp_connection_states()
for state, count in connection_states.items():
    print(f"{state}: {count}")
