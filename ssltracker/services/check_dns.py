import dns.resolver
import nmap

def query_dns_with_nameserver(domain, nameserver):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]

    try:
        a_records = [str(answer) for answer in resolver.resolve(domain, 'A')]
        cname_records = [str(answer) for answer in resolver.resolve(domain, 'CNAME')]
        
        return {
            'A_records': a_records,
            'CNAME_records': cname_records
        }
    except dns.resolver.NoAnswer:
        return f"No records found for {domain}"
    except dns.resolver.NXDOMAIN:
        return f"Domain {domain} does not exist"
    except dns.resolver.Timeout:
        return "DNS query timed out"
    except dns.resolver.DNSException as e:
        return f"DNS query failed: {e}"

# Example usage with a specific DNS server (replace '8.8.8.8' with the desired DNS server)
domain_name = "www.canon.ca"
dns_server = "8.8.8.8"

# Query for both A and CNAME records using the specified DNS server
dns_records = query_dns_with_nameserver(domain_name, dns_server)
print(f"DNS records for {domain_name} using {dns_server}: {dns_records}")

url = "https://" + domain_name


def scan(target):
    nm = nmap.PortScanner()
    nm.scan(hosts=target, arguments='-p 22-8080')

    for host in nm.all_hosts():
        print(f"Host: {host}")
        print(f"State: {nm[host].state()}")
        
        for proto in nm[host].all_protocols():
            print(f"Protocol: {proto}")
            ports = nm[host][proto].keys()
            for port in ports:
                print(f"Port: {port} - State: {nm[host][proto][port]['state']}")

# Example usage
target_host = domain_name
scan(target_host)
