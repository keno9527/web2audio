# web2audio Chrome extension

第一版 Chrome 插件用于从当前网页提取文章标题、来源 URL、正文和常见元信息，并提交到 web2audio 后端的 `POST /api/articles`。

## 本地加载

1. 打开 Chrome `chrome://extensions`。
2. 开启 Developer mode。
3. 选择 Load unpacked，目录选择仓库中的 `extension/`。
4. 更新插件代码后，在扩展卡片上点击刷新图标重新加载插件。
5. 启动后端服务后，在普通 `http` 或 `https` 文章页打开插件弹窗，确认 API 地址和 token。

默认配置：

- API 地址：`http://127.0.0.1:8000`
- Token：`dev-token`

## 验证

从仓库根目录运行：

```bash
node --test extension/tests/*.test.cjs
```

## 常见提示

- `chrome://`、Chrome Web Store、扩展管理页等浏览器内部页面不支持正文提取，需要切换到普通网页。
- 如果当前网页在插件安装或重新加载前已经打开，插件会尝试自动注入正文提取脚本并重试提交。
