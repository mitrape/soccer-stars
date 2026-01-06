import socket
import json

HOST = "127.0.0.1"
PORT = 9000

def send(sock, data):
    sock.sendall((json.dumps(data) + "\n").encode())

def recv(sock):
    return json.loads(sock.recv(4096).decode())

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

while True:
    print("\n1) Register")
    print("2) Login")
    print("3) List users")
    print("4) Set busy")
    print("5) Logout")
    choice = input("> ")

    if choice == "1":
        send(sock, {
            "type": "REGISTER",
            "username": input("username: "),
            "email": input("email: "),
            "password": input("password: ")
        })
        print(recv(sock))

    elif choice == "2":
        send(sock, {
            "type": "LOGIN",
            "username": input("username: "),
            "password": input("password: ")
        })
        print(recv(sock))

    elif choice == "3":
        send(sock, {"type": "LIST_USERS"})
        print(recv(sock))

    elif choice == "4":
        send(sock, {"type": "SET_STATUS", "status": "busy"})
        print("Status set to busy")

    elif choice == "5":
        send(sock, {"type": "LOGOUT"})
        break

sock.close()
