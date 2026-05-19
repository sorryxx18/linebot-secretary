# 消防大隊行政小秘書 LINE Bot

LINE Bot 搭配 Google Drive 雲端資料庫，協助消防大隊快速回覆議員備詢。

## 功能

- 直接輸入問題，自動搜尋資料庫產出正式公務格式報告
- `/同步` 從 Google Drive 下載最新文件
- `/重建索引` 重新建立搜尋索引
- `/文件清單` 查看已索引文件
- 傳送圖片，自動辨識公文表格內容

## 安裝（Windows）

### 前置需求

1. [Python 3.11+](https://www.python.org/downloads/)
2. LINE Developers 帳號（免費）
3. Google Cloud Platform 帳號（免費）
4. Cloudflare 帳號（免費）

### 步驟

**1. 下載程式**
```
git clone https://github.com/your-org/linebot-secretary.git
cd linebot-secretary
```

**2. 安裝**
```
setup.bat
```

**3. 填入 .env**

| 項目 | 取得方式 |
|------|---------|
| LINE_CHANNEL_SECRET | LINE Developers Console |
| LINE_CHANNEL_ACCESS_TOKEN | 同上 |
| GOOGLE_API_KEY | Google AI Studio（免費）|
| GOOGLE_SA_KEY | GCP Console Service Account JSON 路徑 |
| DRIVE_FOLDER_ID | Drive 資料夾網址最後一段 |

**4. 啟動**
```
start.bat
```

**5. 初始化**

在 LINE 傳：`/同步`
