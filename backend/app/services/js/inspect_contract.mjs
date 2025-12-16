import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';

dotenv.config();

const secretKey = process.env.THIRDWEB_SECRET_KEY;
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const chainName = process.env.CHAIN_NAME || "sepolia";


const sdk = new ThirdwebSDK(chainName, {
    secretKey: secretKey,
});//初始化 SDK

async function inspect() {
    try {
        const contract = await sdk.getContract(contractAddress);//获取合约实例
        console.log("Contract Type:", contract.abi.length);//打印合约 ABI 长度，用于判断合约类型

        const type = await contract.call("contractType");//调用合约的 contractType 函数
        console.log("Contract Type String:", type);
        
        // List all functions in the ABI
        const functions = contract.abi.filter(item => item.type === 'function').map(f => f.name);
        //过滤出所有类型为 function 的函数名
        console.log("Available Functions:", functions);

    } catch (error) {
        console.error("Inspection failed:", error);
    }
}

inspect();