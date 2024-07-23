import subprocess

# Step 1: Run the command and capture the output
result = subprocess.run(['df', '-i'], capture_output=True, text=True)

print(result.stdout)
# вот так и будем кетчить, а потом парсить строку))
