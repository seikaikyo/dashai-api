---
title: API Gateway 整合優化
type: refactor
status: in-progress
created: 2026-03-18
---

# API Gateway 整合優化

## 變更內容

5 個子模組各自維護 config、database、middleware，導致連線浪費、CORS 重複定義、middleware 重疊。
統一整合為共用架構，減少資源消耗和維護成本。

## 分階段實施

### Phase 1: DB 連線池統一 (高優先)
- JLPT 移除獨立 engine，改用共用 `database.py`
- 預估省下 10 個 DB 連線 (pool_size=5 + max_overflow=5)

### Phase 2: RedTeam stats 查詢合併 (高優先)
- 3 個獨立查詢合併為 1 個
- 預估延遲降低 60%

### Phase 3: 移除冗餘 main.py (中優先)
- 刪除 `jlpt/main.py` 和 `english/main.py` 的獨立 app 設定
- 這兩個模組只需保留 router，由 gateway 統一掛載
- 減少約 600 行冗餘碼

### Phase 4: Config 統一 (中優先)
- 5 個 config.py 合為 1 個 `config.py`
- CORS origins 從 21 處重複定義改為 1 處
- 子模組改用 `from config import get_settings`

### Phase 5: Middleware 統一 (中優先)
- 3 個 SecurityHeadersMiddleware 合為 1 個
- 放在 gateway 層統一套用，子模組不重複套用

## 影響範圍

| 檔案 | 變更 |
|------|------|
| `database.py` | 確認為唯一 engine 來源 |
| `config.py` | 整合所有子模組設定 |
| `main.py` | 統一 middleware 註冊 |
| `jlpt/models/database.py` | 移除獨立 engine，改 import 共用 |
| `jlpt/main.py` | 刪除（保留 router.py） |
| `english/main.py` | 刪除（保留 router.py） |
| `english/config.py` | 刪除，改用共用 config |
| `factory/config.py` | 刪除，改用共用 config |
| `shukuyo/config.py` | 刪除，改用共用 config |
| `redteam/config.py` | 刪除，改用共用 config |
| `redteam/middleware.py` | 刪除，由 gateway 統一處理 |
| `redteam/routers/stats.py` | 合併 3 個查詢為 1 個 |

## 測試計畫

每個 Phase 完成後：
1. 本機 `uvicorn main:app` 啟動無報錯
2. 各子模組 API 端點回應正確
   - `curl /redteam/api/stats`
   - `curl /jlpt/api/questions`
   - `curl /english/api/health`
   - `curl /factory/api/dashboard`
   - `curl /shukuyo/api/fortune`
3. 推送後 Render 部署成功
4. 線上各端點驗證

## Checklist
- [ ] Phase 1: JLPT DB engine 統一
- [ ] Phase 2: RedTeam stats 查詢合併
- [ ] Phase 3: 移除 jlpt/main.py、english/main.py
- [ ] Phase 4: Config 統一
- [ ] Phase 5: Middleware 統一
