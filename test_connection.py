import socket
import time
import subprocess

def test_port(port, max_retries=10):
    """Test if Chrome debugging port is open"""
    print(f"Kiểm tra port {port}...")
    
    for i in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ Port {port} đã mở!")
                return True
            else:
                print(f"   Lần {i+1}/{max_retries}: Port chưa mở, đợi 2 giây...")
                time.sleep(2)
        except Exception as e:
            print(f"   Lần {i+1}/{max_retries}: Lỗi {e}")
            time.sleep(2)
    
    print(f"❌ Port {port} không mở sau {max_retries} lần thử!")
    return False

def main():
    print("="*60)
    print("  TEST KẾT NỐI CHROME")
    print("="*60)
    print()
    
    # Check if Chrome is running
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], 
                          capture_output=True, text=True)
    
    if "chrome.exe" not in result.stdout:
        print("❌ Chrome KHÔNG CHẠY!")
        print("Chạy OPEN_CHROME.bat trước!")
        input("Nhấn ENTER...")
        return
    
    print("✅ Chrome đang chạy")
    print()
    
    # Test port 9222
    if test_port(9222):
        print()
        print("="*60)
        print("  SẴN SÀNG! Bây giờ chạy RUN_ALL.bat")
        print("="*60)
    else:
        print()
        print("="*60)
        print("  LỖI! Chrome chạy nhưng port 9222 không mở")
        print("  Đóng Chrome và chạy lại OPEN_CHROME.bat")
        print("="*60)
    
    input("\nNhấn ENTER...")

if __name__ == "__main__":
    main()
