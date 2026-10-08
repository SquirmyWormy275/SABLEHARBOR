"""Serve two workrooms and drain HTTP, background jobs and owned threads."""

import asyncio
import contextlib
import hashlib
import signal
import socket

from workspace_lifecycle import require

MODES = ("CLEAN", "MESSY")
PORTS = {"CLEAN": 8782, "MESSY": 8783}


class RootStop:
    def __init__(self):
        self.signals = []
        self.servers = []
        self.loop = None
        self.requested = False

    def request(self, signum=None, _frame=None):
        self.requested = True
        if signum is not None:
            self.signals.append(signal.Signals(signum).name)

        def exit_servers():
            for server in self.servers:
                server.should_exit = True

        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(exit_servers)
        else:
            exit_servers()


async def serve_and_drain(apps, stop, on_ready, index_sha256):
    """Owned uvicorn sessions; no force cancellation or timed automatic STOP."""
    import uvicorn

    class RootServer(uvicorn.Server):
        @contextlib.contextmanager
        def capture_signals(self):
            yield

        async def shutdown(self, sockets=None):
            await super().shutdown(sockets=sockets)
            self.root_shutdown_settled = True

    sockets = {}
    servers = {}
    tasks = {}
    stop.loop = asyncio.get_running_loop()
    try:
        for mode in MODES:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets[mode] = sock
            sock.bind(("127.0.0.1", PORTS[mode]))
            sock.setblocking(False)
            servers[mode] = RootServer(
                uvicorn.Config(
                    apps[mode],
                    host="127.0.0.1",
                    port=PORTS[mode],
                    workers=1,
                    reload=False,
                    access_log=False,
                    log_config=None,
                    log_level="critical",
                    timeout_graceful_shutdown=None,
                )
            )
        stop.servers = list(servers.values())
        require(not stop.requested, "Root STOP before startup")
        tasks = {
            mode: asyncio.create_task(server.serve(sockets=[sockets[mode]]))
            for mode, server in servers.items()
        }
        while not all(server.started for server in servers.values()):
            require(not stop.requested, "Root STOP before readiness")
            for task in tasks.values():
                if task.done():
                    task.result()
                    raise RuntimeError("Server exited before paired readiness")
            await asyncio.sleep(0.05)
        observations = {}
        for mode in MODES:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", PORTS[mode]), 10
            )
            try:
                writer.write(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                await writer.drain()
                header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
                require(
                    len(header) <= 65536 and header.split(b"\r\n")[0] == b"HTTP/1.1 200 OK",
                    "Genuine loopback root response required",
                )
                length = [
                    line.split(b":", 1)[1].strip()
                    for line in header.split(b"\r\n")
                    if line.lower().startswith(b"content-length:")
                ]
                require(
                    len(length) == 1 and length[0].isdigit() and 0 < int(length[0]) <= 1024**2,
                    "Finite real frontend response required",
                )
                body = await asyncio.wait_for(reader.readexactly(int(length[0])), 10)
                require(
                    await asyncio.wait_for(reader.read(1), 10) == b""
                    and hashlib.sha256(body).hexdigest() == index_sha256,
                    "Served frontend bytes differ",
                )
                observations[mode] = {
                    "port": PORTS[mode],
                    "HTTP_status": 200,
                    "index_sha256": index_sha256,
                    "response_bytes": len(body),
                    "authenticated_or_UI_acceptance": False,
                }
            finally:
                writer.close()
                await writer.wait_closed()
        require(
            not stop.requested and not any(task.done() for task in tasks.values()),
            "Stopped before real READY closure",
        )
        on_ready(observations)
        await asyncio.wait(tasks.values(), return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.request()  # exceptional cleanup is not a successful Root STOP receipt
        try:
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            for mode, server in servers.items():
                if server.started and not getattr(server, "root_shutdown_settled", False):
                    await server.shutdown(sockets=[sockets[mode]])
            for app in apps.values():
                pending = tuple(t for t in app.state.generation_jobs.values() if not t.done())
                require(
                    all(t.get_loop() is asyncio.get_running_loop() for t in pending),
                    "Same serving-loop jobs required",
                )
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                jobs = app.state.background_jobs
                if jobs is not None:
                    with jobs.mutex:
                        threads = tuple(jobs.threads.values())
                    for thread in threads:
                        await asyncio.to_thread(thread.join)
                    with jobs.mutex:
                        require(
                            not any(t.is_alive() for t in jobs.threads.values()),
                            "Background jobs unsettled",
                        )
            require(
                all(
                    not server.server_state.tasks
                    and not server.server_state.connections
                    and not server.force_exit
                    for server in servers.values()
                ),
                "HTTP request drain incomplete",
            )
            for task in tasks.values():
                task.result()
        finally:
            for sock in sockets.values():
                sock.close()
            stop.loop = None
