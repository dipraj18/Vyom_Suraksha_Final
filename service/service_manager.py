# service/service_manager.py

"""
Module: ServiceManager (Service Control Layer)

Purpose:
- Manages lifecycle of Vyom_Suraksha service
"""

import logging


class ServiceManager:
    def __init__(self, daemon):
        self.daemon = daemon

    def start_service(self):
        logging.info("Starting Vyom_Suraksha service...")
        self.daemon.start()

    def stop_service(self):
        logging.info("Stopping Vyom_Suraksha service...")
        self.daemon.stop()

    def restart_service(self):
        logging.info("Restarting Vyom_Suraksha service...")
        self.stop_service()
        self.start_service()