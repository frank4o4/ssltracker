import requests
import json

api_key = "BYX5KQKELE3M5Y2HGLOJVTBY2JPCELSTQMJPRFI6ZNKX2V5LNJGFK4ACBA5T25IMFWKNHL3KKM2YUPYAB"
url = "https://www.digicert.com/services/v2/domain"

headers = {
    'X-DC-DEVKEY': api_key,
    'Content-Type': "application/json"
}
response = requests.get(url, headers=headers)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Use response.json() to get the JSON content as a Python dictionary
    json_response = response.json()

    # Access the "domains" key
    domains_data = json_response.get("domains", [])

    # Define a simple class to represent the data structure
    class UserData:
        def __init__(self, id, is_active, name, date_created, container_name, validations):
            self.id = id
            self.is_active = is_active
            self.name = name
            self.date_created = date_created
            self.container_name = container_name
            self.validations = validations

    user_instances = []
    for entry in domains_data:
        validations_until_list = [
            validation['validated_until'] for validation in entry.get('validations', [])
        ]
        user_instance = UserData(
            entry['id'],
            entry['is_active'],
            entry['name'],
            entry['date_created'],
            entry['container']['name'],
            validations_until_list,
        )
        user_instances.append(user_instance)

    # Now you can work with the instances as needed
    for user in user_instances:
        print(f"ID: {user.id}, Active: {user.is_active}, Name: {user.name}, "
              f"Date Created: {user.date_created}, Container Name: {user.container_name}, "
              f"Validations Until: {user.validations}")
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)
