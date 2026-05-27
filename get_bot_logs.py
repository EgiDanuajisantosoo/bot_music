import paramiko

def check_screen_logs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("103.186.31.46", port=19013, username="ubuntu", password="egi@VPS", timeout=10)
        # Clear old screen log first
        ssh.exec_command("rm -f /home/ubuntu/screen_log.txt")
        # Dump screen history (screen hardcopy saves the current terminal screen)
        # We can also use screen's log feature or write a scrollback dump
        # To get the full scrollback, we can enable logging or use screen -X hardcopy
        stdin, stdout, stderr = ssh.exec_command("screen -S musicbot -X hardcopy /home/ubuntu/screen_log.txt && cat /home/ubuntu/screen_log.txt")
        content = stdout.read().decode('utf-8', errors='replace')
        print("=== SCREEN CONTENT ===")
        print(content)
        ssh.close()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    check_screen_logs()
