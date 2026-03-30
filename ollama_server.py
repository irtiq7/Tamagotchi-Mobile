#!/usr/bin/env python3
"""
Ollama Server - OPTIMIZED FOR SPEED
Fast responses for Tamagotchi
"""

import asyncio
import os
import signal
from aiohttp import web, ClientSession, ClientTimeout
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_PORT = 11434
OLLAMA_URL = f"http://127.0.0.1:{OLLAMA_PORT}"
MODEL_NAME = "smollm"
API_PORT = 8000


class OllamaServer:
    def __init__(self):
        self.ollama_process = None
        self.http_session = None
        self.shutdown_event = asyncio.Event()
        self.started_ollama = False

    async def start_ollama_if_needed(self):
        logger.info("Checking Ollama status...")
        
        try:
            async with ClientSession() as session:
                async with session.get(f"{OLLAMA_URL}/api/tags", timeout=ClientTimeout(total=2)) as r:
                    if r.status == 200:
                        logger.info("✓ Ollama already running!")
                        self.started_ollama = False
                        return
        except Exception:
            logger.info("Starting Ollama...")
        
        try:
            self.ollama_process = await asyncio.create_subprocess_exec(
                "ollama", "serve",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.started_ollama = True
            await self.wait_until_ready()
            logger.info("✓ Ollama started!")
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            raise

    async def wait_until_ready(self, max_attempts=30):
        for attempt in range(max_attempts):
            try:
                async with ClientSession() as session:
                    async with session.get(f"{OLLAMA_URL}/api/tags", timeout=ClientTimeout(total=2)) as r:
                        if r.status == 200:
                            return True
            except Exception:
                pass
            await asyncio.sleep(1)
        raise TimeoutError("Ollama failed to start")

    async def chat_handler(self, request):
        """OPTIMIZED chat handler"""
        try:
            data = await request.json()
            messages = data.get("messages", [])

            if not messages:
                return web.json_response({"error": "No messages"}, status=400)

            # SPEED OPTIMIZATIONS
            async with self.http_session.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 30,
                        "top_k": 10,
                        "top_p": 0.9,
                        "num_ctx": 512
                    }
                },
                timeout=ClientTimeout(total=15)
            ) as r:
                if r.status != 200:
                    error_text = await r.text()
                    logger.error(f"Ollama error: {error_text}")
                    return web.json_response({"error": error_text}, status=r.status)
                
                result = await r.json()
                return web.json_response(result)

        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return web.json_response({"error": "Timeout"}, status=504)
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def health_handler(self, request):
        try:
            async with self.http_session.get(f"{OLLAMA_URL}/api/tags", timeout=ClientTimeout(total=2)) as r:
                if r.status == 200:
                    return web.json_response({
                        "status": "healthy",
                        "model": MODEL_NAME
                    })
        except Exception:
            pass
        return web.json_response({"status": "unhealthy"}, status=503)

    async def shutdown_handler(self, app):
        logger.info("Shutting down...")
        
        if self.http_session:
            await self.http_session.close()
        
        if self.ollama_process and self.started_ollama:
            self.ollama_process.terminate()
            try:
                await asyncio.wait_for(self.ollama_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.ollama_process.kill()
                await self.ollama_process.wait()
        
        logger.info("✓ Shutdown complete")


async def create_app(server):
    app = web.Application()
    app.router.add_post("/chat", server.chat_handler)
    app.router.add_get("/health", server.health_handler)
    app.on_cleanup.append(server.shutdown_handler)
    return app


async def main():
    server = OllamaServer()
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("\nShutdown signal received")
        server.shutdown_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: signal_handler())

    try:
        await server.start_ollama_if_needed()
        
        server.http_session = ClientSession(timeout=ClientTimeout(total=20))
        
        app = await create_app(server)
        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, "0.0.0.0", API_PORT)
        await site.start()

        logger.info("=" * 60)
        logger.info(f"✓ FAST CHAT SERVER: http://127.0.0.1:{API_PORT}")
        logger.info(f"✓ Model: {MODEL_NAME}")
        logger.info("=" * 60)

        await server.shutdown_event.wait()

    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        if 'runner' in locals():
            await runner.cleanup()


if __name__ == '__main__':
    print("🚀 Starting FAST Ollama Server...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        exit(1)
