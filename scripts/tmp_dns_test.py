import socket
import sys

def check_dns(hostname):
    print(f"Checking DNS for {hostname}...")
    try:
        addr = socket.gethostbyname(hostname)
        print(f"Success: {hostname} resolved to {addr}")
        return True
    except socket.gaierror as e:
        print(f"Error: Could not resolve {hostname}: {e}")
        return False

if __name__ == "__main__":
    targets = [
        "generativelanguage.googleapis.com",
        "google.com",
        "openrouter.ai",
        "api.openai.com"
    ]
    
    all_ok = True
    for target in targets:
        if not check_dns(target):
            all_ok = False
            
    if not all_ok:
        print("\nSome DNS lookups failed. This explains the 'getaddrinfo failed' error.")
        sys.exit(1)
    else:
        print("\nAll DNS lookups successful.")
        sys.exit(0)
