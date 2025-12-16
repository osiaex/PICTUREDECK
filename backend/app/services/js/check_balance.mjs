//========此脚本用于检查用户钱包余额==============
//========敏感要求：只能在后端运行，需要配置 secret key、private key==============

import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';

dotenv.config();

// 解决 BigInt 报错问题 (这也是一个好习惯，放在所有脚本开头)
BigInt.prototype.toJSON = function() { return this.toString(); }

const secretKey = process.env.THIRDWEB_SECRET_KEY;
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const rpcUrl = process.env.RPC_URL || "sepolia";
const privateKey = process.env.PRIVATE_KEY;

if (!secretKey || !contractAddress || !privateKey) {
    console.error("Error: Missing .env configuration");
    process.exit(1);
}

const sdk = ThirdwebSDK.fromPrivateKey(privateKey, rpcUrl, {
    secretKey: secretKey,
});// 从私钥初始化 SDK

async function checkBalance() {
    try {
        const walletAddress = await sdk.wallet.getAddress();
        console.log(`\nChecking wallet: ${walletAddress}`);
        console.log(`Checking contract: ${contractAddress}\n`);

        const contract = await sdk.getContract(contractAddress);
        
        // 获取该钱包拥有的所有 NFT
        const ownedNFTs = await contract.erc1155.getOwned(walletAddress);

        if (ownedNFTs.length === 0) {
            console.log("You don't own any NFTs in this contract.");
            console.log("Please run 'node mint_nft.mjs' first to mint one.");
        } else {
            console.log(`You own ${ownedNFTs.length} types of NFTs:\n`);
            ownedNFTs.forEach((nft) => {
                console.log(`------------------------------------------------`);
                console.log(`Token ID:   ${nft.metadata.id}`);
                console.log(`Name:       ${nft.metadata.name}`);
                console.log(`Balance（数量）:    ${nft.quantityOwned}`); // 拥有的数量
                console.log(`------------------------------------------------`);
            });
            console.log(`\nTry transferring one of these IDs!`);
            console.log(`Example: node transfer_nft.mjs ${ownedNFTs[0].metadata.id} <ToAddress> 1`);
        }

    } catch (error) {
        console.error("Check Failed:", error);
    }
}

checkBalance();
