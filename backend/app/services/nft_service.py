from pathlib import Path
import requests
from fastapi import HTTPException

from backend.app.core.config import THIRDWEB_CLIENT_ID, THIRDWEB_NFT_CONTRACT

THIRDWEB_API_URL = "https://api.thirdweb.com/storage/upload"

class NFTService:
    def __init__(self):
        if not THIRDWEB_CLIENT_ID:
            raise RuntimeError("THIRDWEB_CLIENT_ID not configured")
        if not THIRDWEB_NFT_CONTRACT:
            raise RuntimeError("THIRDWEB_NFT_CONTRACT is not configured.")
        
        self.client_id = THIRDWEB_CLIENT_ID
        self.nft_contract = THIRDWEB_NFT_CONTRACT
    
    def upload_file(self, file_path: Path) -> str:
        ##上传图片/文件到 thirdweb storage，返回 ipfs://CID 链接
        file_bytes = Path(file_path).read_bytes()

        headers = {
            "x-sdk-name": "thirdweb-python",
            "x-client-id": self.client_id,
        }

        files = {
            "file": (Path(file_path).name, file_bytes)
        }

        response = requests.post(
            THIRDWEB_STORAGE_UPLOAD_URL,
            headers=headers,
            files=files
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Storage upload failed: {response.text}"
            )

        data = response.json()
        # thirdweb 统一返回 ipfs://CID 的格式
        return data.get("uri", None)
    
    ##metadata JSON:不能上链,传到IPFS里面,只有Mint 时传入 metadata URI。
    def upload_metadata(self, metadata: dict) -> str:
        ##上传 metadata JSON 到 thirdweb storage
        headers = {
            "x-sdk-name": "thirdweb-python",
            "x-client-id": self.client_id,
        }

        response = requests.post(
            THIRDWEB_STORAGE_UPLOAD_URL,
            headers=headers,
            json={"metadata": metadata}
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Metadata upload failed: {response.text}"
            )

        return response.json().get("uri", None)
        
    def mint_nft(self, to_address: str, metadata_uri: str) -> dict:
        """
        调用 thirdweb ERC721 合约写入 API 进行 mint。
        返回: token_id, tx_hash, contract_address
        """
        mint_url = f"https://api.thirdweb.com/contract/{self.contract}/erc721/mint"

        headers = {
            "x-client-id": self.client_id,
            "Content-Type": "application/json"
        }

        body = {
            "to": to_address,
            "metadataUri": metadata_uri
        }

        resp = requests.post(mint_url, headers=headers, json=body)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Mint error: {resp.text}"
            )

        return resp.json()