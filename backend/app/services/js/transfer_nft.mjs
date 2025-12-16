//========此脚本用于转账 NFT==============
//========敏感要求：只能在后端运行，需要配置 secret key==============

import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';

dotenv.config();

// 1. 配置检查
const secretKey = process.env.THIRDWEB_SECRET_KEY;
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const rpcUrl = process.env.RPC_URL || "sepolia";
const privateKey = process.env.PRIVATE_KEY;

if (!secretKey || !contractAddress || !privateKey) {
    console.error("Error: Missing .env configuration");
    process.exit(1);
}

// 2. 获取命令行参数
// 格式: node transfer_nft.mjs <tokenId> <toAddress> <num>
const args = process.argv.slice(2);
if (args.length < 2) {
    console.error("Usage: node transfer_nft.mjs <tokenId> <toAddress>");
    process.exit(1);
}
const [tokenId, toAddress,num] = args;

// 3. 初始化 SDK
const sdk = ThirdwebSDK.fromPrivateKey(privateKey, rpcUrl, {
    secretKey: secretKey,
});

async function transfer() {
    try{
        console.log(`Transferring Token ID: ${tokenId} to ${toAddress}`);
        const contract = await sdk.getContract(contractAddress);
        const tx = await contract.erc1155.transfer(toAddress, tokenId, Number(num));
        console.log(`Transfer successful! Transaction Hash: ${tx.receipt.transactionHash}`);
    }
    catch(error){
        console.error("\nTransfer Failed!");
        console.error("\n=====Error Details:=====\n");
        console.error(error);
        process.exit(1);
    }
}

transfer();