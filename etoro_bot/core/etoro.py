import requests
import time
from ..config import ETORO_API_KEY, ETORO_USER_KEY

BASE_URL = "https://public-api.etoro.com/api/v1"

class EtoroAPI:
    def __init__(self, api_key=ETORO_API_KEY, user_key=ETORO_USER_KEY):
        self.api_key = api_key
        self.user_key = user_key
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": self.api_key,
            "x-user-key": self.user_key
        })

    def _request(self, method, endpoint, **kwargs):
        import uuid
        headers = kwargs.get('headers', {})
        headers['x-request-id'] = str(uuid.uuid4())
        kwargs['headers'] = headers
        
        url = f"{BASE_URL}{endpoint}"
        
        for attempt in range(5):
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 429:
                wait_time = 15 * (2 ** attempt)
                time.sleep(min(wait_time, 60))
                continue
            
            response.raise_for_status()
            return response.json()
            
        response.raise_for_status()
        
    def resolve_instrument(self, symbol):
        data = self._request("GET", f"/market-data/search?internalSymbolFull={symbol}")
        items = data.get("items", [])
        for item in items:
            if item.get("internalSymbolFull", "").upper() == symbol.upper():
                return item.get("instrumentId")
        raise ValueError(f"Instrument not found for symbol: {symbol}")

    def get_pnl(self):
        return self._request("GET", "/trading/info/real/pnl")

    def open_position(self, instrument_id, amount, is_buy=True, leverage=1):
        payload = {
            "InstrumentID": instrument_id,
            "IsBuy": is_buy,
            "Leverage": leverage,
            "Amount": amount
        }
        return self._request("POST", "/trading/execution/market-open-orders/by-amount", json=payload)

    def close_position(self, position_id, instrument_id, units_to_deduct=None):
        payload = {
            "InstrumentId": instrument_id,
            "UnitsToDeduct": units_to_deduct if units_to_deduct else None
        }
        return self._request("POST", f"/trading/execution/market-close-orders/positions/{position_id}", json=payload)

    def cancel_order(self, order_id):
        return self._request("DELETE", f"/trading/execution/market-open-orders/{order_id}")
