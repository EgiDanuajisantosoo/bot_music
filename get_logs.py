import paramiko

def fetch_logs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
        
        # Check processes
        stdin, stdout, stderr = ssh.exec_command("tail -n 100 /home/ubuntu/bot-musik/logs/bot.log")
        print("--- BOT LOG ---")
        print(stdout.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_logs()
