# This needs to be put on the computer that you want to accept the shutdown request. (Not the server running the Discord Bot)
from audioop import add
import socket
from os import system

# result = system('cmd /c "curl ifconfig.io"')

# host = socket.gethostbyname(socket.gethostname()) # Sometimes this gets the correct IP address
host = "10.1.0.69"
port = 9000

# create a socket at server side
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# bind socket with server
sock.bind((host, port))

# allow 1 connection
sock.listen(1)

def Main():
    global sock
    conn:socket.socket
    print(f"Server started: {host}:{port}")
    print("Server waiting for connections...")
    while True:
        # check if the client is connected before attempting to receive data
        try:
            conn.sendall(b'ping')
        except:
            conn, addr = sock.accept()
            print("connection from: ", str(addr))

        try:
            data = conn.recv(1024)

            if not data or data == b'exit':
                break

            normalData = data.decode('utf-8')

            # figure out what to do with the message
            print(f"message recieved: {normalData}")
            ProcessCommand(normalData)

        except:
            print("client has disconnected")

    conn.close()
    pass

def ProcessCommand(message:str):
    if message == "shutdown":
        system('cmd /c "shutdown /s /t 0"')
    elif message == "shutdown -f":
        system('cmd /c "shutdown /s /t 0 /f"')
    pass

if __name__ == "__main__":
    Main()