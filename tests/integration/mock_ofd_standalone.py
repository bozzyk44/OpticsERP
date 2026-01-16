"""
Standalone Mock OFD Server for Docker
Runs Flask server without threading (for production-like deployment)
"""

import os
import logging
from mock_ofd_server import MockOFDServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get configuration from environment
    port = int(os.getenv('OFD_PORT', 9000))
    host = os.getenv('OFD_HOST', '0.0.0.0')

    logger.info(f"Starting Mock OFD Server on {host}:{port}")

    # Create and start server (blocking)
    server = MockOFDServer(port=port, host=host)
    server.start()

    # Keep running (server.start() is blocking in standalone mode)
    logger.info("Mock OFD Server is running. Press Ctrl+C to stop.")

    try:
        # Block forever (Flask handles SIGTERM gracefully)
        import signal
        import time

        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping server...")
            server.stop()
            exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping server...")
        server.stop()
