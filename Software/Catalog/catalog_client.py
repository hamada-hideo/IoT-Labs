import requests
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))

class CatalogClient:
    
    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.catalog_ip = data["rest"]["ip"]
        self.catalog_port = data["rest"]["port"]
        self.catalog_endpoint = data["rest"]["endpoint"]
        self.loop_time = data["expiration_time"] // 2
        self.catalog_devices_path = "devices"
        self.catalog_services_path = "services"
        self.catalog_broker_path = "broker"
        self.registered = False

    def _request_json(self, method, full_path, message_spec, data):
        url = f"http://{self.catalog_ip}:{self.catalog_port}/{full_path}"
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            elif method == "PUT":
                response = requests.put(url)
            if response.status_code != 200:
                print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, response status code: {response.status_code}\n")
                return
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, error during request {str(e)}")
        except json.JSONDecodeError:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, response is not a valid json")
        except Exception as e:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality: {str(e)}")

    def _get_request_json(self, full_path, message_spec):
        return self._request_json("GET", full_path, message_spec, None)

    def _post_request_json(self, full_path, message_spec, data):
        return self._request_json("POST", full_path, message_spec, data)

    def _put_request_json(self, full_path, message_spec):
        return self._request_json("PUT", full_path, message_spec, None)

    def get_catalog(self):
        return self._get_request_json(self.catalog_endpoint, "full catalog")
    
    def get_devices(self):
        return self._get_request_json(f"{self.catalog_endpoint}/{self.catalog_devices_path}", "devices catalog")
    
    def get_services(self):
        return self._get_request_json(f"{self.catalog_endpoint}/{self.catalog_services_path}", "services catalog")
    
    def get_device(self, id):
        return self._get_request_json(f"{self.catalog_endpoint}/{self.catalog_devices_path}/{id}", f"device {id} data")
    
    def get_service(self, id):
        return self._get_request_json(f"{self.catalog_endpoint}/{self.catalog_services_path}/{id}", f"service {id} data")
    
    def get_broker(self):
        return self._get_request_json(f"{self.catalog_endpoint}/{self.catalog_broker_path}", "broker data")
    
    def register_device(self, payload):
        return self._post_request_json(f"{self.catalog_endpoint}/{self.catalog_devices_path}", "device registration", payload)
    
    def register_service(self, payload):
        return self._post_request_json(f"{self.catalog_endpoint}/{self.catalog_services_path}", "service registration", payload)
    
    def refresh_device(self, id):
        return self._put_request_json(f"{self.catalog_endpoint}/{self.catalog_devices_path}/{id}", "device refresh")

    def refresh_service(self, id):
        return self._put_request_json(f"{self.catalog_endpoint}/{self.catalog_services_path}/{id}", "service refresh")
