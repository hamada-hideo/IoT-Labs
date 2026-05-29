import urllib.request
import json

class CatalogClient:
    def __init__(self, host, port, root_resource):
        self.base_url = f"http://{host}:{port}/{root_resource}"

    def get_broker(self):
        """Effettua una GET HTTP al catalogo per recuperare l'IP e la porta del broker."""
        try:
            with urllib.request.urlopen(self.base_url) as response:
                if response.status == 200:
                    catalog_data = json.loads(response.read().decode("utf-8"))
                    return catalog_data.get("broker")
        except Exception as e:
            print(f"[CatalogClient Error] Impossibile recuperare il broker: {e}")
        return None

    def register_device(self, payload):
        """Invia un POST HTTP al catalogo per registrare il dispositivo."""
        try:
            url = f"{self.base_url}/devices"
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req) as response:
                if response.status in [200, 201]:
                    print("[CatalogClient] Dispositivo registrato con successo.")
                    return True
        except Exception as e:
            print(f"[CatalogClient Error] Errore durante la registrazione: {e}")
        return False

    def refresh_device(self, device_id):
        """Invia una richiesta HTTP PUT per effettuare il refresh del dispositivo."""
        try:
            url = f"{self.base_url}/devices/{device_id}"
            req = urllib.request.Request(url, method='PUT')
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return True
        except Exception as e:
            print(f"[CatalogClient Error] Errore durante il refresh: {e}")
        return False
