import paramiko
import time

def restart_services():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to VPS...")
        ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
        
        commands = [
            "pkill -f 'Lavalink.jar'",
            "pkill -f 'main.py'",
            "pkill -f 'cloudflared tunnel'",
            "sleep 2"
        ]
        
        print("Killing old processes...")
        for cmd in commands:
            ssh.exec_command(cmd)
            
        time.sleep(3)
        
        print("Starting Lavalink...")
        ssh.exec_command("cd /home/ubuntu/bot-musik && nohup java -jar Lavalink.jar > logs/lavalink_stdout.log 2>&1 &")
        
        print("Waiting for Lavalink to start...")
        time.sleep(15)
        
        print("Starting Bot...")
        ssh.exec_command("cd /home/ubuntu/bot-musik && source venv/bin/activate && pip install -r requirements.txt && nohup python -u main.py > logs/bot.log 2>&1 &")
        
        print("Starting Cloudflare Tunnel...")
        ssh.exec_command("cd /home/ubuntu/bot-musik && nohup cloudflared tunnel --url http://localhost:8081 > cloudflare.log 2>&1 &")
        
        time.sleep(5)
        
        print("Fetching Cloudflare URL...")
        stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/bot-musik && cat cloudflare.log | grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com'")
        cf_urls = stdout.read().decode('utf-8').splitlines()
        
        if cf_urls:
            print("Cloudflare Tunnel URL:", cf_urls[-1])
        else:
            print("Cloudflare Tunnel URL not found yet. Check cloudflare.log on VPS.")
            
        ssh.close()
        print("Restart complete!")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    restart_services()
