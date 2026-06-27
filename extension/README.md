# web2audio Chrome extension

第一版 Chrome 插件用于从当前网页提取文章标题、来源 URL、正文和常见元信息，并提交到 web2audio 后端的 `POST /api/articles`。

## 本地加载

1. 打开 Chrome `chrome://extensions`。
2. 开启 Developer mode。
3. 选择 Load unpacked，目录选择仓库中的 `extension/`。
4. 启动后端服务后，在插件弹窗中确认 API 地址和 token。

默认配置：

- API 地址：`http://127.0.0.1:8000`
- Token：`dev-token`

## 验证

从仓库根目录运行：

```bash
node --test extension/tests/article_extractor.test.cjs
```
