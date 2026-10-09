import ssl
import socket

# Define the target website and port
website = "www.example.com"
port = 443  # Default port for HTTPS

# Create a socket connection to the website
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)  # Set a timeout for the connection

try:
    sock.connect((website, port))
    # Wrap the socket with an SSL context to get the certificate
    context = ssl.create_default_context()
    with context.wrap_socket(sock, server_hostname=website) as ssock:
        cert = ssock.getpeercert()

        # Extract certificate details
        common_name = cert.get('subject')[0][0][1]  # Common Name (CN)
        sans = cert.get('subjectAltName')  # Subject Alternative Names (SANs)
        expiry_date = cert.get('notAfter')  # Expiry date

        print(f"Common Name: {common_name}")
        print(f"Subject Alternative Names: {', '.join([name for _, name in sans]) if sans else 'N/A'}")
        print(f"Expiry Date: {expiry_date}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    sock.close()
