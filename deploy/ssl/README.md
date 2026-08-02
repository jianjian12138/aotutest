# SSL 证书目录

## 用途

此目录用于存放 Nginx TLS 证书，被 `docker-compose.yml` 的 `frontend` 服务以只读方式挂载到 `/etc/nginx/ssl/`。

`frontend/nginx.conf` 和 `deploy/nginx/nginx.conf` 中的 HTTPS server block 引用以下路径：

```
ssl_certificate /etc/nginx/ssl/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

## 证书放置

将你的证书文件放入此目录，文件名必须为：

| 文件名 | 说明 |
|--------|------|
| `fullchain.pem` | 证书链（含中间证书） |
| `privkey.pem` | 私钥文件 |

### 使用 Let's Encrypt (certbot) 生成

```bash
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem  deploy/ssl/
```

### 使用自签名证书（仅开发/测试）

```bash
openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -keyout deploy/ssl/privkey.pem \
  -out    deploy/ssl/fullchain.pem \
  -subj   "/CN=localhost"
```

## 注意事项

- **此目录不应提交真实证书到版本控制**。`.gitignore` 已排除 `*.pem`。
- 证书缺失时 Nginx 启动会报错——这是预期行为，请确保部署前证书已就位。
- 生产环境建议配置自动续期（如 certbot renew + nginx reload cron）。
