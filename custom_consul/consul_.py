from consul import Consul, ConsulException
import requests
import socket
import time


class ConsulServiceRegistry:
    def __init__(self, consul_host='consul-server', consul_port=8500):
        """Initialize the Consul service registry."""
        self.consul = Consul(host=consul_host, port=consul_port)
        self.service_name = None
        self.service_id = None

    def register_service(self, service_name, service_id, port, tags=None, check_interval='10s'):
        """
        Registers a service with Consul.

        :param service_name: Name of the service to register.
        :param service_id: Unique identifier for the service instance.
        :param port: Port the service is listening on.
        :param tags: Optional tags to associate with the service.
        :param check_interval: Health check interval.
        """
        self.service_name = service_name
        self.service_id = service_id
        
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        # Define the health check URL
        health_check_url = f'http://{ip_address}:{port}/health'

        # Register the service with a health check
        try:
            self.consul.agent.service.register(
                service_name,
                service_id=service_id,
                port=port,
                tags=tags,
                check={
                    'http': health_check_url,
                    'interval': check_interval,
                }
            )
            print(
                f"Service {service_name} registered with ID {service_id} on port {port}")
        except ConsulException as e:
            print(f"Error registering service: {e}")

    def deregister_service(self, service_id):
        """Deregisters the service from Consul."""
        try:
            self.consul.agent.service.deregister(service_id)
            print(f"Service with ID {service_id} deregistered.")
        except ConsulException as e:
            print(f"Error deregistering service: {e}")

    def discover_service(self, service_name):
        """
        Discovers a service registered in Consul by its name.

        :param service_name: Name of the service to discover.
        :return: List of service instances with their IPs and ports.
        """
        try:
            services = self.consul.catalog.service(service_name)
            discovered_services = [
                {'id': service['ServiceID'], 'address': service['ServiceAddress'],
                    'port': service['ServicePort']}
                for service in services[1]
            ]
            return discovered_services
        except ConsulException as e:
            print(f"Error discovering service: {e}")
            return []

    def wait_for_service(self, service_name, max_retries=5, wait_interval=2):
        """
        Waits for a service to be registered with Consul.

        :param service_name: Name of the service to wait for.
        :param max_retries: Maximum number of retries before giving up.
        :param wait_interval: Time in seconds to wait between retries.
        :return: True if the service was discovered, False if retries exceeded.
        """
        retries = 0
        while retries < max_retries:
            services = self.discover_service(service_name)
            if services:
                print(f"Service {service_name} found.")
                return services
            retries += 1
            print(f"Waiting for {service_name} to register...")
            time.sleep(wait_interval)
        print(f"Service {service_name} not found after {max_retries} retries.")
        return []


    def wait_for_consul(self, max_retries=10):
        for _ in range(max_retries):
            try:
                r = requests.get("http://consul-server:8500/v1/status/leader")
                if r.status_code == 200 and r.text != '""':
                    print("Consul is ready")
                    return True
            except requests.exceptions.ConnectionError:
                print("Waiting for Consul to start...")
            time.sleep(5)
        raise Exception("Consul did not start in time")
