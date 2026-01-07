# server/server.py  (only the invite state + handlers changed; you can replace whole file if easier)
import asyncio, json, hashlib, secrets
from pathlib import Path

HOST = "0.0.0.0"
PORT = 9000
USERS_FILE = Path(__file__).resolve().parent / "users.json"

users = {}
online = {}
status = {}
user_ip = {}
udp_port = {}

# NEW: invitation sets
# outgoing[from_user] = set(to_users)
outgoing = {}
# incoming[to_user] = from_user  (only allow 1 incoming at a time per target)
incoming = {}

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
    writer.write((json.dumps(data) + "\n").encode("utf-8"))
    await writer.drain()

async def send_to(username: str, data: dict):
    w = online.get(username)
    if w:
        await send(w, data)

def _set_status(u: str, st: str):
    if u in online:
        status[u] = st

def _clear_incoming_for(to_user: str):
    """Remove incoming invite for to_user and corresponding outgoing mapping."""
    from_user = incoming.pop(to_user, None)
    if from_user:
        s = outgoing.get(from_user)
        if s:
            s.discard(to_user)
            if not s:
                outgoing.pop(from_user, None)

def _cancel_all_outgoing(from_user: str):
    """Cancel all invites sent by from_user; notify recipients to close modal."""
    tos = outgoing.pop(from_user, set())
    for to_user in list(tos):
        if incoming.get(to_user) == from_user:
            incoming.pop(to_user, None)
            # notify the recipient
            # (if they later click accept, server will reject anyway)
            asyncio.create_task(send_to(to_user, {"type": "INVITE_CANCELLED", "from": from_user}))

def safe_close(username: str):
    # clear invites involving username
    # 1) cancel all outgoing invites from username
    _cancel_all_outgoing(username)
    # 2) if username had an incoming invite, clear it
    _clear_incoming_for(username)
    status[username] = "free"

    online.pop(username, None)
    status.pop(username, None)
    user_ip.pop(username, None)
    udp_port.pop(username, None)

# ---------- handlers ----------
async def handle_register(msg, writer):
    u = (msg.get("username") or "").strip()
    email = (msg.get("email") or "").strip()
    pw = msg.get("password") or ""
    if not u:
        return await send(writer, {"type": "ERROR", "message": "Username is required"})
    if not email:
        return await send(writer, {"type": "ERROR", "message": "Email is required"})
    if not pw:
        return await send(writer, {"type": "ERROR", "message": "Password is required"})
    if u in users:
        return await send(writer, {"type": "ERROR", "message": "Username already exists"})
    users[u] = {"email": email, "password": hash_password(pw)}
    save_users()
    await send(writer, {"type": "OK", "message": "Registered successfully"})

async def handle_login(msg, writer, addr):
    u = (msg.get("username") or "").strip()
    pw = msg.get("password") or ""
    if u not in users:
        await send(writer, {"type": "ERROR", "message": "User not found"})
        return None
    if users[u]["password"] != hash_password(pw):
        await send(writer, {"type": "ERROR", "message": "Wrong password"})
        return None

    # kick old session
    if u in online and online[u] is not writer:
        try:
            await send(online[u], {"type": "ERROR", "message": "Logged in elsewhere"})
            online[u].close()
        except Exception:
            pass
        safe_close(u)

    online[u] = writer
    status[u] = "free"
    user_ip[u] = addr[0]
    await send(writer, {"type": "OK", "message": "Login successful"})
    return u

async def handle_set_udp_port(msg, username, writer):
    if not username:
        return await send(writer, {"type": "ERROR", "message": "Login first"})
    try:
        p = int(msg.get("udp_port"))
        if p <= 0 or p > 65535:
            raise ValueError()
    except Exception:
        return await send(writer, {"type": "ERROR", "message": "Invalid udp_port"})
    udp_port[username] = p
    await send(writer, {"type": "OK", "message": f"UDP port set to {p}"})

async def handle_list_users(writer):
    data = [{"username": u, "status": status.get(u, "free")} for u in online.keys()]
    await send(writer, {"type": "USERS", "users": data})

async def handle_invite(msg, username, writer):
    if not username:
        return await send(writer, {"type": "ERROR", "message": "Login first"})

    to_user = msg.get("to")
    if not to_user or to_user not in online:
        return await send(writer, {"type": "ERROR", "message": "User not online"})
    if to_user == username:
        return await send(writer, {"type": "ERROR", "message": "Cannot invite yourself"})

    if status.get(username) != "free":
        return await send(writer, {"type": "ERROR", "message": "You are busy"})
    if status.get(to_user) != "free":
        return await send(writer, {"type": "ERROR", "message": "User is busy"})

    # Target can have only 1 incoming invite at a time
    if to_user in incoming:
        return await send(writer, {"type": "ERROR", "message": "User already has a pending invite"})

    incoming[to_user] = username
    outgoing.setdefault(username, set()).add(to_user)

    await send_to(to_user, {"type": "INVITE_RECEIVED", "from": username})
    await send(writer, {"type": "OK", "message": f"Invite sent to {to_user}"})

async def handle_invite_response(msg, username, writer):
    if not username:
        return await send(writer, {"type": "ERROR", "message": "Login first"})

    from_user = msg.get("from")
    accepted = bool(msg.get("accepted", False))

    # Validate that username currently has an invite from from_user
    if incoming.get(username) != from_user:
        return await send(writer, {"type": "ERROR", "message": "Invite expired or not found"})

    # Remove this invite from tables (whether accepted or declined)
    _clear_incoming_for(username)

    if not accepted:
        await send_to(from_user, {"type": "INVITE_DECLINED", "by": username})
        return await send(writer, {"type": "OK", "message": "Invite declined"})

    # Re-check free state at accept time (race-safe)
    if status.get(from_user) != "free" or status.get(username) != "free":
        await send(writer, {"type": "ERROR", "message": "Cannot start match: one player is busy"})
        await send_to(from_user, {"type": "ERROR", "message": "Match failed: player busy"})
        return

    if from_user not in udp_port or username not in udp_port:
        await send(writer, {"type": "ERROR", "message": "UDP port missing (both players must set it)"})
        await send_to(from_user, {"type": "ERROR", "message": "Match failed: UDP port missing"})
        return

    # IMPORTANT FIX:
    # As soon as match starts, inviter becomes busy and ALL other outgoing invites must be cancelled.
    _set_status(from_user, "busy")
    _set_status(username, "busy")
    _cancel_all_outgoing(from_user)  # cancels remaining invites from inviter
    _cancel_all_outgoing(username)   # (optional) cancels any from accepter too

    match_id = secrets.token_hex(4)

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

async def handle_match_end(msg, username):
    """
    Called when a client finishes a match.
    Frees this user and clears any pending invites involving them.
    """
    if not username:
        return

    global pending_invite, status

    # mark user as free
    status[username] = "free"

    # remove any pending invites involving this user
    for to_u, from_u in list(pending_invite.items()):
        if to_u == username or from_u == username:
            pending_invite.pop(to_u, None)

async def client_handler(reader, writer):
    addr = writer.get_extra_info("peername")
    username = None
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception:
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
            elif cmd == "INVITE":
                await handle_invite(msg, username, writer)
            elif cmd == "INVITE_RESPONSE":
                await handle_invite_response(msg, username, writer)
            elif cmd == "LOGOUT":
                await handle_logout(username)
                break
            elif cmd == "MATCH_END":
                await handle_match_end(msg, username)
            else:
                await send(writer, {"type": "ERROR", "message": "Unknown command"})
    finally:
        await handle_logout(username)
        writer.close()
        await writer.wait_closed()

async def main():
    load_users()
    server = await asyncio.start_server(client_handler, HOST, PORT)
    print(f"Server running on {HOST}:{PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())