from typing import Any

import requests

CUSTOM_PACK_ENDPOINT = ("https://ygoprodeck.com/api/pack-sim/getPackInfo.php")

class YgoProDeckClient:
    def __init__(self, timeout: float = 15.0, session: requests.Session | None = None) -> None:
        self._timeout = timeout
        self._session = session or requests.Session()

    def fetch_custom_pack_raw(self, external_id: str) -> list[dict[str, Any]]:
        response = self._session.get(
            CUSTOM_PACK_ENDPOINT,
            params={"id": external_id},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("YGOPRODeck custom pack response must be a list.")
        return data
    