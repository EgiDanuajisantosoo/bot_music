import paramiko

def download_file():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("103.186.31.46", port=19013, username="ubuntu", password="egi@VPS", timeout=10)
        sftp = ssh.open_sftp()
        sftp.get("/home/ubuntu/bot-musik/main.py", "main_web.py")
        sftp.close()
        ssh.close()
        print("Success downloading main_web.py")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    download_file()
