from collections import namedtuple
from typing import Optional

from providers.http_client_w_backoff import AsyncClientWithBackoff

DeliveredPayloadsResponse = namedtuple("DeliveredPayloadsResponse",
                                       [
                                           "slot",
                                           "block_hash",
                                           "builder_pubkey",
                                           "proposer_fee_recipient",
                                           "value",
                                           "block_number",
                                       ]
                                       )


class MevRelay:
    def _get_http_client(self) -> AsyncClientWithBackoff:
        return AsyncClientWithBackoff(
            timeout=5
        )

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.client = self._get_http_client()

    async def get_payload(self, block_hash: str) -> Optional[DeliveredPayloadsResponse]:
        resp = await self.client.get_w_backoff(url=f"{self.api_url}/relay/v1/data/bidtraces/proposer_payload_delivered", params={
            "block_hash": block_hash,
        })

        if resp.status_code != 200:
            raise Exception(
                f"Error while fetching data from MEV relay ({self.api_url}): {resp.content.decode()}"
            )

        data = resp.json()
        if len(data) == 0:
            return None
        else:
            # Block hash -> only 1 block expected
            assert len(data) == 1
            raw = data[0]

            response = DeliveredPayloadsResponse(
                slot=int(raw["slot"]),
                block_hash=raw["block_hash"],
                builder_pubkey=raw["builder_pubkey"],
                proposer_fee_recipient=raw["proposer_fee_recipient"],
                value=int(raw["value"]),
                block_number=int(raw["block_number"]),
            )
            assert response.block_hash == block_hash
            return response

