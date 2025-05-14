import consul
import socket


def register_to_consul(service_name, service_id, port):
    consul_client = consul.Consul(host='consul-server', port=8500)

    ip_address = "cassandra_node"
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=ip_address,
        port=port
    )
    print(f"+ Registered {service_name} at {ip_address}:{port}", flush=True)


if __name__ == "__main__":
    register_to_consul(service_name='cassandra',
                       service_id='cassandra',
                       port=9042)
