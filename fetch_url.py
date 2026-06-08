import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/bot-musik && cat cloudflare.log | grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com'")
lines = stdout.read().decode('utf-8').splitlines()
if lines:
    print("URL:", lines[-1])
else:
    print("No URL found yet.")
ssh.close()
