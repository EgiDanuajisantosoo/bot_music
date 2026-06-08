import paramiko
import re

def get_cf_url():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
        stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/bot-musik && grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' cloudflare.log | tail -n 1")
        url = stdout.read().decode('utf-8').strip()
        if url:
            print(f"URL: {url}")
        else:
            print("URL Not Found")
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_cf_url()
