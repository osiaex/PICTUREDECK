import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';

dotenv.config();

const secretKey = process.env.THIRDWEB_SECRET_KEY;
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const rpcUrl = process.env.RPC_URL || "sepolia";
const privateKey = process.env.PRIVATE_KEY;

const sdk = ThirdwebSDK.fromPrivateKey(privateKey, rpcUrl, {
    secretKey: secretKey,
});

async function fixMetadata() {
    try {
        console.log("🛠️  Connecting to contract...");
        const contract = await sdk.getContract(contractAddress);

        console.log("📦 Fetching current contract metadata (via raw call to avoid Zod crash)...");
        // 1. 获取当前的 contractURI (指向 IPFS 的链接)
        const currentURI = await contract.call("contractURI");
        console.log("Current URI:", currentURI);

        // 2. 构造一个新的、干净的 metadata 对象
        // 既然原来的读不出来（一读就崩），我们干脆手写一个新的覆盖它
        const newMetadata = {
            name: "WcattestNFT", // 你之前的合约名字
            description: "Sprint 2 Test", // 你之前的描述
            // 关键点：显式设置版税为数字 0
            seller_fee_basis_points: 0, 
            fee_recipient: await sdk.wallet.getAddress(),
            symbol: "WCN" // 假设的 symbol，或者你可以通过 contract.call("symbol") 获取
        };

        console.log("📝 Uploading new sanitized metadata to IPFS...");
        // SDK 的 storage 工具可以帮我们上传 JSON 并返回 IPFS URI
        const newUri = await sdk.storage.upload(newMetadata);
        console.log("New IPFS URI:", newUri);

        console.log("🔗 Updating contractURI on-chain...");
        // 3. 调用 setContractURI 把合约指向新的 Metadata
        await contract.call("setContractURI", [newUri]);

        console.log("✅ Contract Metadata reset successfully!");
        console.log("👉 Now the SDK should be able to read the contract without Zod errors.");

    } catch (error) {
        console.error("❌ Metadata fix failed:", error);
    }
}

fixMetadata();