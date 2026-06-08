import paramiko
import time

def restart():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
        print("Killing main.py...")
        ssh.exec_command('pkill -f main.py')
        time.sleep(2)
        print("Starting main.py...")
        ssh.exec_command('cd /home/ubuntu/bot-musik && nohup bash -c "source venv/bin/activate && python -u main.py" > logs/bot.log 2>&1 &')
        time.sleep(2)
        ssh.close()
        print("Bot restarted!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restart()
