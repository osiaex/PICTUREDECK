//========此脚本用于获取合约的元数据（名称、符号等）==============
//========敏感要求：只能在后端运行，需要配置secret key==============
import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';

dotenv.config();

const secretKey = process.env.THIRDWEB_SECRET_KEY;
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const chainName = process.env.CHAIN_NAME || "sepolia";

if (!secretKey) {
    console.error("THIRDWEB_SECRET_KEY is not set");
    process.exit(1);
}

if (!contractAddress) {
    console.error("THIRDWEB_NFT_CONTRACT is not set");
    process.exit(1);
}

// SDK 初始化
const sdk = new ThirdwebSDK(chainName, {
    secretKey: secretKey,
});

try {
    const contract = await sdk.getContract(contractAddress);
    
    // 修改点：不再调用 contract.metadata.get()，因为它会触发 Zod 校验错误
    // 而是直接调用合约的基础读取函数 name() 和 symbol()
    const name = await contract.call("name");
    const symbol = await contract.call("symbol");

    // 构造一个简单的元数据对象返回
    const metadata = {
        name: name,
        symbol: symbol,
        description: "Metadata fetched via direct calls (bypassing Zod validation)",
        image: "" // 暂时留空，避免复杂的 URI 解析
    };

    console.log("\n"+"hey, this is the metadata of the 合约!\n"+JSON.stringify(metadata));
} catch (error) {
    console.error("Error fetching contract data:", error);
    process.exit(1);
}
