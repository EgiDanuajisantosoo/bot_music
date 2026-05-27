import paramiko
import os

def upload_files():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect('103.186.31.46', port=19013, username='ubuntu', password='egi@VPS', timeout=10)
        sftp = ssh.open_sftp()
        
        # Files to upload
        files = [
            ('requirements.txt', '/home/ubuntu/bot-musik/requirements.txt'),
            ('.env', '/home/ubuntu/bot-musik/.env'),
            ('public/style.css', '/home/ubuntu/bot-musik/public/style.css'),
            ('public/script.js', '/home/ubuntu/bot-musik/public/script.js')
        ]
        
        # Ensure public directory exists
        try:
            sftp.stat('/home/ubuntu/bot-musik/public')
        except IOError:
            sftp.mkdir('/home/ubuntu/bot-musik/public')
            
        for local, remote in files:
            sftp.put(local, remote)
            print(f"Uploaded {local}")
            
        sftp.close()
        
        ssh.close()
        print("Upload successful!")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    upload_files()
