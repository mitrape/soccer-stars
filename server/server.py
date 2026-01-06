import asyncio
import json
import hashlib
import secrets
from pathlib import Path

HOST = "0.0.0.0"
PORT = 9000
USERS_FILE = Path("server/users.json")

# ---------- Data ----------
users = {}          # username -> {email, password_hash}
online = {}         # username -> writer
status = {}         # username -> "free" | "busy"
user_ip = {}        # username -> ip
udp_port = {}       # username -> udp_port (int)

pending_invite = {} # to_user -> from_user


# ---------- Helpers ----------
def load_users():
    global users
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f).get("users", {})
    else:
        users = {}


def save_users():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, indent=2)


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


async def send(writer, data: dict):
    msg = json.dumps(data) + "\n"
    writer.write(msg.encode())
    await writer.drain()


async def send_to(username: str, data: dict):
    w = online.get(username)
    if w:
        await send(w, data)


def safe_close(username: str):
    online.pop(username, None)
    status.pop(username, None)
    user_ip.pop(username, None)
    udp_port.pop(username, None)
    # clear pending invites involving this user
    for to_u, from_u in list(pending_invite.items()):
        if to_u == username or from_u == username:
            pending_invite.pop(to_u, None)


# ---------- Command handlers ----------
async def handle_register(msg, writer):
    u = msg.get("username", "").strip()
    email = msg.get("email", "").strip()
    pw = msg.get("password", "")

    if not u:
        await send(writer, {"type": "ERROR", "message": "Username is required"})
    return

    if not email:
        await send(writer, {"type": "ERROR", "message": "Email is required"})
    return

    if not pw:
        await send(writer, {"type": "ERROR", "message": "Password is required"})
    return


    if u in users:
        await send(writer, {"type": "ERROR", "message": "Username already exists"})
        return

    users[u] = {"email": email, "password": hash_password(pw)}
    save_users()
    await send(writer, {"type": "OK", "message": "Registered successfully"})


async def handle_login(msg, writer, addr):
    u = msg.get("username", "").strip()
    pw = msg.get("password", "")

    if u not in users:
        await send(writer, {"type": "ERROR", "message": "User not found"})
        return None

    if users[u]["password"] != hash_password(pw):
        await send(writer, {"type": "ERROR", "message": "Wrong password"})
        return None

    # kick old session if exists
    if u in online and online[u] is not writer:
        try:
            await send(online[u], {"type": "ERROR", "message": "Logged in elsewhere"})
            online[u].close()
        except:
            pass
        safe_close(u)

    online[u] = writer
    status[u] = "free"
    user_ip[u] = addr[0]
    await send(writer, {"type": "OK", "message": "Login successful"})
    return u


async def handle_list_users(writer):
    data = [{"username": u, "status": status.get(u, "free")} for u in online.keys()]
    await send(writer, {"type": "USERS", "users": data})


async def handle_set_udp_port(msg, username, writer):
    if not username:
        await send(writer, {"type": "ERROR", "message": "Login first"})
        return

    try:
        p = int(msg.get("udp_port"))
        if p <= 0 or p > 65535:
            raise ValueError()
    except:
        await send(writer, {"type": "ERROR", "message": "Invalid udp_port"})
        return

    udp_port[username] = p
    await send(writer, {"type": "OK", "message": f"UDP port set to {p}"})


async def handle_set_status(msg, username):
    if username:
        s = msg.get("status")
        if s in ("free", "busy"):
            status[username] = s


async def handle_invite(msg, username, writer):
    if not username:
        await send(writer, {"type": "ERROR", "message": "Login first"})
        return

    to_user = msg.get("to")
    if not to_user or to_user not in online:
        await send(writer, {"type": "ERROR", "message": "User not online"})
        return

    if to_user == username:
        await send(writer, {"type": "ERROR", "message": "Cannot invite yourself"})
        return

    if status.get(username) != "free":
        await send(writer, {"type": "ERROR", "message": "You are busy"})
        return

    if status.get(to_user) != "free":
        await send(writer, {"type": "ERROR", "message": "User is busy"})
        return

    # store pending
    pending_invite[to_user] = username

    # notify target
    await send_to(to_user, {"type": "INVITE_RECEIVED", "from": username})
    await send(writer, {"type": "OK", "message": f"Invite sent to {to_user}"})


async def handle_invite_response(msg, username, writer):
    if not username:
        await send(writer, {"type": "ERROR", "message": "Login first"})
        return

    from_user = msg.get("from")  # inviter
    accepted = bool(msg.get("accepted", False))

    # validate pending invite
    if pending_invite.get(username) != from_user:
        await send(writer, {"type": "ERROR", "message": "No such pending invite"})
        return

    pending_invite.pop(username, None)

    if not accepted:
        await send_to(from_user, {"type": "INVITE_DECLINED", "by": username})
        await send(writer, {"type": "OK", "message": "Invite declined"})
        return

    # accepted => need udp ports
    if from_user not in udp_port or username not in udp_port:
        await send(writer, {"type": "ERROR", "message": "UDP port missing (both players must set it)"})
        await send_to(from_user, {"type": "ERROR", "message": "Match failed: UDP port missing"})
        return

    # mark busy
    status[from_user] = "busy"
    status[username] = "busy"

    match_id = secrets.token_hex(4)

    # send match start to both with the other peer's info
    await send_to(from_user, {
        "type": "MATCH_START",
        "match_id": match_id,
        "peer_username": username,
        "peer_ip": user_ip[username],
        "peer_udp_port": udp_port[username],
        "you_start": True
    })
    await send_to(username, {
        "type": "MATCH_START",
        "match_id": match_id,
        "peer_username": from_user,
        "peer_ip": user_ip[from_user],
        "peer_udp_port": udp_port[from_user],
        "you_start": False
    })

    await send(writer, {"type": "OK", "message": "Match starting"})


async def handle_logout(username):
    if username:
        safe_close(username)


# ---------- Client handler ----------
async def client_handler(reader, writer):
    addr = writer.get_extra_info("peername")
    print("Connected:", addr)

    username = None

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                msg = json.loads(line.decode())
            except:
                await send(writer, {"type": "ERROR", "message": "Bad JSON"})
                continue

            cmd = msg.get("type")
            if cmd == "REGISTER":
                await handle_register(msg, writer)

            elif cmd == "LOGIN":
                username = await handle_login(msg, writer, addr)

            elif cmd == "SET_UDP_PORT":
                await handle_set_udp_port(msg, username, writer)

            elif cmd == "LIST_USERS":
                await handle_list_users(writer)

            elif cmd == "SET_STATUS":
                await handle_set_status(msg, username)

            elif cmd == "INVITE":
                await handle_invite(msg, username, writer)

            elif cmd == "INVITE_RESPONSE":
                await handle_invite_response(msg, username, writer)

            elif cmd == "LOGOUT":
                await handle_logout(username)
                break

            else:
                await send(writer, {"type": "ERROR", "message": "Unknown command"})

    except Exception as e:
        print("Error:", e)

    finally:
        await handle_logout(username)
        writer.close()
        await writer.wait_closed()
        print("Disconnected:", addr)


# ---------- Main ----------
async def main():
    load_users()
    server = await asyncio.start_server(client_handler, HOST, PORT)
    print(f"Server running on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
