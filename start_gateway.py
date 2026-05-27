#!/usr/bin/env python3
"""
Message Channel Gateway - Entry point

Routes Telegram/WeChat/etc. messages to bayesian-agi-core engine.
Usage:
    python start_gateway.py [--config config.yaml]
"""
import argparse
import asyncio
import logging
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gateway.config import load_gateway_config
from src.gateway.server import GatewayServer


def main():
    parser = argparse.ArgumentParser(description="Message Channel Gateway")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    config = load_gateway_config(args.config)

    if args.debug:
        config.debug = True

    server = GatewayServer(config)

    async def shutdown(sig):
        logging.info(f"Received signal {sig}, shutting down...")
        await server.stop()
        sys.exit(0)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(server.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(server.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
