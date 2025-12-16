from functools import partial
import subprocess
import json
import os
import time

from sqlalchemy import exc

import asyncio
import subprocess
import uuid
from collections import defaultdict

class NFTService:
    
    #函数：检查env中对应钱包的balance（资产）(必须保证已经设置好了private key)
    def check_balance(self, address: str):
        return self.call_js_script("check_balance.mjs", [address])

    #函数：查看合同的metadata(必须保证已经设置好了secret key，需要手动在/js/.env中设置合同的THIRDWEB_NFT_CONTRACT)
    def get_nft_metadata(self, token_id: str):
        return self.call_js_script("contract_metadata.mjs", [token_id])

    #函数：铸造 NFT(必须保证已经设置好了private key、secret key)
    def mint_nft(self, name, description, image_path):
        return self.call_js_script("mint_nft.mjs", [name, description, image_path])

    #函数：转账 NFT(必须保证已经设置好了private key、secret key)
    def transfer_nft(self, token_id, to_address, amount=1):
        return self.call_js_script("transfer_nft.mjs", [token_id, to_address, amount])  


    ####################实现代码######################
    
    #NFT模块必需的密钥设置：privatekey（用户的钱包密钥）和secretkey（后端加速密钥）
    def update_env(self, private_key: str, secret_key: str):
               # 读取现有文件
        if os.path.exists(self.env_path):
            with open(self.env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        new_lines = []
        found = False
        
        # 逐行检查，如果找到 key 就替换
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        
        # 如果没找到，就追加到最后
        if not found:
            # 确保前一行有换行符
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f"{key}={value}\n")

        # 写回文件
        with open(self.env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Updated .env: {key} updated successfully.")


    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.js_dir=os.path.join(self.script_dir,"js")
        self.env_path=os.path.join(self.js_dir,'.env')
    
    def call_js_script(self,script_name,args=[]):
        """
        调用 JS 文件夹下的脚本
        script_name: 脚本名字 (例如 'transfer_nft.mjs')
        args: 参数列表 (例如 [27, '0xabc...', 1])
        """
        command=["node",script_name]+[str(arg) for arg in args]

        print("执行"+script_name+ ' '.join(command))
        try:
            result=subprocess.run(
                command,
                cwd=self.js_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            return result.stdout
        
        except subprocess.CalledProcessError as e:
            print(f"脚本执行失败: {e}")
            print(f"标准错误输出: {e.stderr}")
            raise

    async def async_execute(self, func, callback=None, *args, **kwargs):
        """
        异步执行 NFTService 的任意方法，并在结束时调用回调
        func: 方法本身，如 self.mint_nft
        callback: 回调函数（可选），形式为 callback(result)
        """
        loop = asyncio.get_running_loop()

        wrapped = partial(func, *args, **kwargs)
        
        # 将同步方法封装到线程池执行
        result = await loop.run_in_executor(None, wrapped)

        # 执行回调
        if callback:
            try:
                callback(result)
            except Exception as e:
                print("回调函数错误:", e)

        return result



if __name__ == "__main__":

    # 创建服务实例
    service = NFTService()

    # print("\n====== TEST: mint_nft ======")
    # try:
    #     result = service.mint_nft("Test_4_spend_time", "4: This is a test_4 NFT", "D:\\AllZiLiao\\MyProgram\\NewSoftwareEngineering\\AIGC_Client\\local_result\\e124f35b_d657_4d5d_b18d_c2a2886f9b82.jpg")
    #     print("mint_nft 返回：", result)
    # except Exception as e:
    #     print("mint_nft 测试失败：", e)

    # print("\n====== TEST: get_nft_metadata ======")
    # try:  
    #     result = service.get_nft_metadata("31")
    #     print("get_nft_metadata 返回：", result)
    # except Exception as e:
    #     print("get_nft_metadata 测试失败：", e)

    print("\n====== TEST: transfer_nft ======")
    try:  
        result = service.transfer_nft("41", "0x92098227688A14FE94122A4e590bf604674AF9e1", 1)
        print("transfer_nft 返回：", result)
    except Exception as e:
        print("transfer_nft 测试失败：", e)

    print("====== TEST: check_balance ======")
    try:  
        result = service.check_balance("0x63107216004a144BA683673562E277267797c6DB")
        print("check_balance 返回：", result)
    except Exception as e:
        print("check_balance 测试失败：", e)






