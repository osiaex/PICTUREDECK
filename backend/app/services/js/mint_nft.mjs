//========此脚本用于铸造 NFT==============
//========敏感要求：只能在后端运行，需要配置 secret key、private key==============

import dotenv from 'dotenv';
import { ThirdwebSDK } from '@thirdweb-dev/sdk';
import fs from 'fs';

dotenv.config();
console.error("Script started");

const secretKey = process.env.THIRDWEB_SECRET_KEY;//xf!
const contractAddress = process.env.THIRDWEB_NFT_CONTRACT;
const chainName = process.env.CHAIN_NAME || "sepolia";
const privateKey = process.env.PRIVATE_KEY;// xf!
// 优先使用 .env 中的 chainName，如果不存在则回退到 RPC_URL
const rpcUrl =  chainName || process.env.RPC_URL;

if (!secretKey || !contractAddress || !privateKey) {
    console.error("Error: Missing configuration in .env (need PRIVATE_KEY)");
    process.exit(1);
}

//脚本命令执行格式： node mint_nft.mjs "作品名称" "描述" "文件本地路径"
const args = process.argv.slice(2);//切掉前2个输入参数(隐藏生成，node文件路径，js文件路径)，保留从第3个参数开始的所有参数
if(args.length<3){
    console.error("Error: Missing arguments");
    process.exit(1);
}//args如果小于3个，就报错

const [name,  description, image] = args;
console.error("Args parsed:", name, description, image);

console.error("Initializing SDK with Private Key...");
// 使用私钥初始化 SDK，以便有权限进行写入操作 (Mint)
// 第一个参数如果是 URL 字符串，会被识别为自定义 RPC
const sdk = ThirdwebSDK.fromPrivateKey(privateKey, rpcUrl, {
    secretKey: secretKey,
});
console.error("SDK Initialized");


async function mint(){
    console.error("Starting mint process...\n");
    console.error("Contract Address:", contractAddress);
    try{
        const contract = await sdk.getContract(contractAddress);
        const walletAddress = await sdk.wallet.getAddress();//用户钱包地址
        console.error("\n"+"hey, this is the walletAddress of the user!\n"+walletAddress);
        //获取钱包地址
        
        //构造此图片的metadata(!!不是合同的metadata!!)，包含名称、描述和图片URI
        let imageInput = image;
        if (fs.existsSync(image)) {
            // 如果是本地文件路径，读取文件内容
            imageInput = fs.readFileSync(image);
            console.error("Image loaded from local file.");
        }

        const metadata = {
            name: name,
            description: description,
            image: imageInput,
        };

        // 检测到这是一个 DropERC1155 (Edition Drop) 合约
        // 这种合约需要先 Lazy Mint (定义元数据)，然后 Claim (铸造/领取)
        console.error("Detected Edition Drop contract. Executing Lazy Mint + Claim flow...");

        // 1. Lazy Mint (创建 NFT 元数据，但此时供应量为 0)
        // 注意：Zod 验证可能会因为 metadata 中的字段类型问题报错
        // 确保所有字段类型正确
        console.error("\n=====STEP1: Preparing metadata for Lazy Mint=====\n");
        const metadataToMint = {
             name: name,
             description: description,
             image: imageInput,
             // 显式设置 seller_fee_basis_points 为数字 0，防止 SDK 自动推断出错 
             seller_fee_basis_points: 0, 
             fee_recipient: walletAddress
        };

        const txs = await contract.erc1155.lazyMint([metadataToMint]);//lazyMint返回的是一个交易数组txs，里面的每个元素是一个交易对象
        const tx = txs[0]; // 取txs的第一个元素（因为我们只传了一个 metadata）
        const tokenId = tx.id;
        
        console.error(`Lazy Minted Token ID: ${tokenId}\n`);

        // 2. 设置 Claim Conditions (铸造规则)
        // Drop 合约必须先设置规则，才能允许 claim。
        // 设置一个最简单的规则：立即开始，无限制，免费。
        console.error("\n=====STEP2: Setting claim conditions=====\n");
        const claimConditions = [{
            startTime: new Date(), // 立即开始
            maxClaimableSupply: 100, // 这个 token 最多能铸造 100 个
            price: 0, // 免费
            quantityLimitPerTransaction: 1, // 每次只能铸造 1 个
            waitInSeconds: 0, // 无需等待
        }];
        console.error("===Claim conditions set:===");
        console.error("token id is"+tokenId);
        console.error("claimConditions is"+JSON.stringify(claimConditions));
        await contract.erc1155.claimConditions.set(tokenId, claimConditions);
        console.error("Claim conditions set successfully.");

        // 3. Claim (为用户铸造 1 个代币)
        console.error("\n=====STEP3: Claiming NFT=====\n");
        const claimTx = await contract.erc1155.claimTo(walletAddress, tokenId, 1);
        
        const receipt = claimTx.receipt;
        
        // 获取最终的 NFT 数据
        const nft = await contract.erc1155.get(tokenId);

        //输出 JSON 结果给 Python
        const result={
            success:true,
            tokenId:tokenId.toString(),
            transactionHash:receipt.transactionHash,
            owner:walletAddress,
            metadata:nft.metadata,
        }

        console.log(JSON.stringify(result));
    }
    catch (error) {
        console.error("\nMinting Failed!");
        
        // 1. 打印完整的错误对象，不仅仅是 message
        // 这样可以看到如果是 ZodError，里面具体的 issues 数组
        if (error.issues) {
            console.error("Validation Issues (Zod Error):");
            console.error(JSON.stringify(error.issues, null, 2));
        } else {
            console.error("\n=====Error Details:=====\n");
            console.error(error);
        }

        process.exit(1);
    }

}

mint();
