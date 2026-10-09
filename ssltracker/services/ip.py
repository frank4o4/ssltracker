import socket

def get_ip_address(domain):
    try:
        ip_address = socket.gethostbyname(domain)
        return ip_address
    except socket.error as e:
        print(f"Error: {e}")
        return None

# Example usage
domain_name = "www.example.com"
ip_address = get_ip_address(domain_name)

if ip_address:
    print(f"The IP address of {domain_name} is: {ip_address}")
else:
    print(f"Unable to resolve the IP address for {domain_name}")
