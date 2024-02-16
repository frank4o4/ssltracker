import requests
import json
import datetime

api_key = "BYX5KQKELE3M5Y2HGLOJVTBY2JPCELSTQMJPRFI6ZNKX2V5LNJGFK4ACBA5T25IMFWKNHL3KKM2YUPYAB"
url = "https://daas.digicert.com/apicontroller/v1/certificate/list"

# Define your payload as a dictionary
payload = {
    "pageSize": 5,
    "divisionIds": [],
    "accountId": 448270,
    
}

# Convert the payload to JSON
payload_json = json.dumps(payload)

headers = {
    'X-DC-DEVKEY': api_key,
    'Content-Type': "application/json",
    }

response = requests.request("POST", url, data=payload_json, headers=headers)


if response.status_code == 200:
    data = response.json()

    print(data)

    # certificate_details_list = data.get('data', {}).get('certificateDetailsDTOList', [])

    # for certificate_details in certificate_details_list:
    #     cert_id = certificate_details.get('certId', '')
    #     cn = certificate_details.get('cn', '')
    #     san  = certificate_details.get('san', '')
    #     valid_from_timestamp = certificate_details.get('validFrom', 0)
    #     expiry_date_timestamp = certificate_details.get('expiryDate', 0)
        
        
        
    #     # Convert timestamp to datetime
    #     valid_from = datetime.datetime.utcfromtimestamp(valid_from_timestamp / 1000)
    #     expiry_date = datetime.datetime.utcfromtimestamp(expiry_date_timestamp / 1000)

   
    #     print(cert_id,cn,san,valid_from,expiry_date)
        
        