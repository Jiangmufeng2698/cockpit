# 大庆营销驾驶舱 - 后端部署指南

## 架构概览

```
用户浏览器 (GitHub Pages)
    │
    ├── 静态资源 (HTML/CSS/JS) ← GitHub Pages CDN
    │
    └── API请求 (HTTPS) ← 云服务器 (FastAPI + MySQL)
            │
            ├── /api/auth/login     → JWT登录
            ├── /api/auth/me        → 令牌验证
            ├── /api/auth/change-password → 改密
            └── /api/data/report    → 获取营销数据
```

## 安全改进对比

| 项目 | 改造前 | 改造后 |
|------|--------|--------|
| 密码存储 | Base64明文 (btoa) | bcrypt哈希 (rounds=12) |
| 密码传输 | 前端编码后比对 | HTTPS + 后端验证 |
| 暴力破解 | 无防护 | 5次失败锁定15分钟 |
| 登录态 | localStorage可伪造 | JWT令牌+服务端验证 |
| 用户信息 | 前端硬编码密码 | 后端数据库，前端无密码 |
| 数据加密 | XOR密钥前端可见 | 后端存储，JWT鉴权获取 |
| 会话安全 | 无服务端验证 | JWT 18小时过期 |
| 密码策略 | 仅排除123456 | ≥6位，含字母+数字 |
| CSP | 无 | 已添加meta标签 |
| XSS防护 | innerHTML渲染用户名 | textContent安全渲染 |

## 部署步骤

### 1. 购买云服务器

推荐阿里云/腾讯云轻量应用服务器：
- 配置：2核2G，够用（59个账号 + 小数据量）
- 系统：Ubuntu 22.04 LTS
- 价格：约50-60元/月
- 需要开放端口：8000（API）、443（HTTPS）

### 2. 安装Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker

# 安装docker-compose
sudo apt install docker-compose -y
```

### 3. 部署后端

```bash
# 上传代码到服务器
scp -r cockpit-backend/ user@your-server:/opt/cockpit-api/

# 进入目录
cd /opt/cockpit-api/

# 创建.env配置文件
cp .env.example .env
nano .env
# 修改以下内容：
# DB_PASSWORD=你的强密码
# JWT_SECRET=随机32位以上字符串

# 启动服务
docker-compose up -d

# 初始化数据库（导入54个用户）
docker-compose exec api python init_db.py
```

### 4. 配置HTTPS（重要！）

```bash
# 安装nginx
sudo apt install nginx -y

# 安装certbot获取免费SSL证书
sudo apt install certbot python3-certbot-nginx -y

# 配置nginx反向代理
sudo nano /etc/nginx/sites-available/cockpit-api
```

nginx配置内容：
```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/cockpit-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 获取SSL证书
sudo certbot --nginx -d api.your-domain.com
```

### 5. 配置前端API地址

在前端 `index.html` 中修改后端地址：
```javascript
// 找到这行（约第2466行）
var API_BASE = window.localStorage.getItem('cockpit_api_base') || 'https://your-server-ip:8000';
// 改为你的实际域名
var API_BASE = 'https://api.your-domain.com';
```

或者不改代码，在浏览器控制台设置：
```javascript
localStorage.setItem('cockpit_api_base', 'https://api.your-domain.com')
```

### 6. 推送前端到GitHub Pages

```bash
cd cockpit-repo
git add index.html
git commit -m "feat: 后端JWT认证 + 安全加固"
git push origin master
```

### 7. 上传营销数据

登录后通过API上传数据（全市权限用户）：
```bash
curl -X POST https://api.your-domain.com/api/data/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@report_data.json"
```

或通过Agent自动化推送。

## 日常运维

### 查看日志
```bash
docker-compose logs -f api
docker-compose logs -f db
```

### 添加/修改用户
```bash
# 进入MySQL
docker-compose exec db mysql -ucockpit -p cockpit

# SQL操作
INSERT INTO users (username, name, dept, scope, password_hash, is_first_login)
VALUES ('newuser', '新用户', '市场部', '萨尔图',
        '$2b$12$...bcrypt_hash...', true);

-- 修改区县权限
UPDATE users SET scope='让胡路' WHERE username='someuser';

-- 禁用账号
UPDATE users SET is_active=false WHERE username='someuser';
```

### 备份数据库
```bash
docker-compose exec db mysqldump -ucockpit -p cockpit > backup_$(date +%Y%m%d).sql
```

### 更新代码
```bash
cd /opt/cockpit-api
git pull  # 或重新上传代码
docker-compose up -d --build
```

## 故障排查

| 问题 | 排查方法 |
|------|---------|
| 前端无法连接后端 | 检查API_BASE地址、CORS配置、防火墙端口 |
| 登录报"无法连接服务器" | 检查后端是否运行 `docker-compose ps` |
| CORS错误 | 在config.py中添加前端域名到CORS_ORIGINS |
| 数据加载失败 | 检查JWT令牌是否过期，后端是否有数据 |
| 锁定无法登录 | 等待15分钟或清空login_attempts表 |
