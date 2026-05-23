import requests
import json

class CatalogClient:
    
    def __init__(self):
        self.catalog_ip = "127.0.0.1"
        self.catalog_port = 8080
        self.catalog_endpoint = "catalog"
        self.catalog_devices_path = "devices"
        self.catalog_services_path = "services"
        self.catalog_broker_path = "broker"

    def _request_json(self, method, full_path, message_spec, data):
        url = f"http://{self.catalog_ip}:{self.catalog_port}/{full_path}"
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            if response.status_code != 200:
                print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, response status code: {response.status_code}")
                return
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, error during request {str(e)}")
        except json.JSONDecodeError:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality, response is not a valid json")
        except:
            print(f"Warning: Error during {method} request to {url} for {message_spec} functionality")

    def _get_request_json(self, full_path, message_spec):
        return self._request_json("GET", full_path, message_spec, None)

    def _post_request_json(self, full_path, message_spec, data):
        return self._request_json("POST", full_path, message_spec, data)

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
        return self._post_request_json(f"{self.catalog_endpoint}/{self.catalog_devices_path}", "device refresh", {"id": id})
    
    def refresh_service(self, id):
        return self._post_request_json(f"{self.catalog_endpoint}/{self.catalog_services_path}", "service refresh", {"id": id})

if __name__ == "__main__":
    cc = CatalogClient()
    print(cc.get_catalog())
    print(cc.get_devices())
    print(cc.get_services())
    print(cc.get_device("pippo"))
    print(cc.get_service("pippo"))
    print(cc.get_broker())
    print(cc.register_device({"data": "pippo"}))
    print(cc.register_service({"data": "pippo"}))
    print(cc.refresh_device("pippo"))
    print(cc.refresh_service("pippo"))