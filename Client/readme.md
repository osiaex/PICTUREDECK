# 配置说明（config.json）

本项目使用 `config.json` 控制应用运行环境、后端地址和调试选项。  
首次运行程序时，如没有发现配置文件，会自动生成默认配置。

---

## config.json 示例

```json
{
    "environment": "offline",
    "debug": true,
    "api_base_urls": {
        "offline": "http://127.0.0.1:8000/api/v1",
        "staging": "https://127.0.0.1:5000/api/v1",
        "production": "https://prod-server.com/api/v1"
    }
}
```

## 参数说明
1. environment（运行环境）

| 可选值          |  说明                              |
| :-------------- | :-------------------------------- |
| `offline` | 离线模式：不连接后端，前端通过 mock_reply 模拟全部网络返回。|
| `staging` | 测试环境：用于连到后端测试服务器，调试真实接口。 |
| `production` | 测试环境：用于连到后端测试服务器，调试真实接口。 |

2. api_base_urls（后端地址配置）

程序内部会根据当前environment自动选择对应的URL。

3. debug（调试标志）

理论上，启用后可打印更多调试日志、开启 UI 额外信息等。但实际上没有用到它。
