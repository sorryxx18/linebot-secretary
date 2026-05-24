import json
import os
import threading
import traceback
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import PlainTextResponse
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    ShowLoadingAnimationRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent

import rag

# 每個 LINE 用戶的對話記憶（最近 5 輪）
_CHAT_HISTORY: dict[str, list[tuple[str, str]]] = defaultdict(list)
_HISTORY_LOCK = threading.Lock()
_HISTORY_MAX = 5

load_dotenv()

BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "二大隊行政小秘書")
UNIT_NAME = os.getenv("UNIT_NAME", "第二救災救護大隊")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:3002").rstrip("/")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
DRIVE_FOLDER_URL = os.getenv("DRIVE_FOLDER_URL", f"{PUBLIC_BASE_URL}/health")

# ── 白名單 ──────────────────────────────────────────────────────────────────
PASSPHRASE = "/tfdfire7236/"
_ALLOWLIST_PATH = Path(os.getenv("DATA_DIR", "/app/data")) / "allowlist.json"
_ALLOWLIST_LOCK = threading.Lock()


def _load_allowlist() -> set[str]:
    try:
        if _ALLOWLIST_PATH.exists():
            return set(json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def _save_allowlist(ids: set[str]) -> None:
    _ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ALLOWLIST_PATH.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _is_allowed(user_id: str) -> bool:
    with _ALLOWLIST_LOCK:
        return user_id in _load_allowlist()


def _add_to_allowlist(user_id: str) -> None:
    with _ALLOWLIST_LOCK:
        ids = _load_allowlist()
        ids.add(user_id)
        _save_allowlist(ids)

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN are required")


@asynccontextmanager
async def lifespan(app: FastAPI):
    rag.reindex_all(force=False)
    yield


app = FastAPI(title=f"{UNIT_NAME}行政小秘書 LINE Bot", version="0.2.0", lifespan=lifespan)
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def check_admin(x_admin_token: str | None) -> None:
    # Always require token — never allow access when ADMIN_TOKEN is unset
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="admin token required")


def _extract_card_summary(reply_text: str) -> str:
    """從回覆內容提取摘要，跳過樣板開頭與章節標題，抓第一段有實質內容的文字。"""
    import re
    skip_prefixes = ("報告人", "日期", "以上報告", "資料來源", "小秘書建議", "建議")
    # 樣板開頭：「根據…說明如下」「依據…報告如下」等（不論後面是否還有文字）
    boilerplate_re = re.compile(r"^(根據|依據|茲就|按|查|經查|報告).{0,30}(說明如下|報告如下|如下)[：:]")
    # 章節標題：一、二、三、（一）（二）等
    section_re = re.compile(r"^[一二三四五六七八九十]+[、。]|^\([一二三四五六七八九十]+\)")

    lines = []
    for line in reply_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(s) for s in skip_prefixes):
            continue
        if line.startswith("-") or line.startswith("•"):
            continue
        if boilerplate_re.match(line):
            continue
        if section_re.match(line):
            continue
        lines.append(line)
        if len(lines) >= 2:
            break
    summary = " ".join(lines)
    return summary[:80] + "…" if len(summary) > 80 else summary or "已依雲端資料庫檢索並產出正式報告。"


def make_summary_card(query: str, reply_text: str = "") -> FlexMessage:
    title = query.strip()[:36] or "小秘書分析回報"
    summary = _extract_card_summary(reply_text) if reply_text else "已依雲端資料庫檢索並產出正式報告。"
    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"👩‍💼 {BOT_DISPLAY_NAME}", "weight": "bold", "size": "lg", "color": "#1F4E79"},
                {"type": "text", "text": "📝 深度報告摘要", "weight": "bold", "size": "md", "color": "#333333"},
                {"type": "separator"},
                {"type": "text", "text": title, "wrap": True, "size": "md", "weight": "bold"},
                {"type": "text", "text": summary, "wrap": True, "size": "sm", "color": "#444444"},
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1F7AE0",
                    "action": {"type": "uri", "label": "📂 開啟雲端資料庫", "uri": DRIVE_FOLDER_URL},
                }
            ],
        },
    }
    return FlexMessage(alt_text=f"{BOT_DISPLAY_NAME}：{title}", contents=FlexContainer.from_dict(bubble))


def split_line_messages(text: str, limit: int = 4800, max_parts: int = 5) -> list[TextMessage]:
    parts = []
    remaining = text.strip()
    while remaining and len(parts) < max_parts:
        if len(remaining) <= limit:
            parts.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut < 1200:
            cut = limit
        parts.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining and len(parts) == max_parts:
        parts[-1] = parts[-1][: limit - 40].rstrip() + "\n……（後續內容因 LINE 限制截斷）"
    return [TextMessage(text=p) for p in parts] or [TextMessage(text="小秘書目前無回覆內容。")]


def build_reply(user_text: str, user_id: str = "") -> tuple[str, bool]:
    """Return (reply_text, show_card). show_card=False for system commands."""
    text = (user_text or "").strip()
    if not text:
        return "請輸入密語以啟用小秘書。", False

    # ── 白名單驗證 ────────────────────────────────────────────────────────────
    if text == PASSPHRASE:
        if user_id and not _is_allowed(user_id):
            _add_to_allowlist(user_id)
            return f"✅ 已啟用{BOT_DISPLAY_NAME}服務。\n\n請直接輸入問題，例如：有什麼水源匱乏地區嗎", False
        return f"您已在白名單中，{BOT_DISPLAY_NAME}已為您服務。", False

    if user_id and not _is_allowed(user_id):
        return f"您尚未取得使用授權，請聯繫系統管理員。", False
    # ─────────────────────────────────────────────────────────────────────────

    if text in {"/狀態", "狀態", "status"}:
        s = rag.stats()
        return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

資料庫狀態：
- 原始檔案：{s['raw_files']} 件
- 已索引文件：{s['documents']} 件
- 索引片段：{s['chunks']} 段
- Webhook：{PUBLIC_BASE_URL}/webhook

可直接輸入問題，例如：有什麼水源匱乏地區嗎

以上報告。""", False

    if text in {"/重建索引", "重建索引", "reindex"}:
        s = rag.reindex_all(force=True)
        return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

已完成資料庫重建索引。
- 原始檔案：{s['raw_files']} 件
- 已索引文件：{s['documents']} 件
- 索引片段：{s['chunks']} 段

以上報告。""", False

    if text in {"/同步", "同步", "/sync", "sync", "/下載", "下載"}:
        try:
            import drive_sync
            result = drive_sync.sync_folder(rag.RAW_DIR)
            s = rag.reindex_all(force=True)
            files_str = "\n".join(f"  - {f}" for f in result["files"][:20]) or "  （無新增）"
            err_str = f"\n錯誤：{len(result['errors'])} 筆" if result["errors"] else ""
            return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

已完成 Google Drive 同步並重建索引。

雲端資料夾：{result['total']} 個檔案
- 已下載：{result['downloaded']} 個
- 略過（格式不支援）：{result['skipped']} 個{err_str}

已索引文件總計：{s['documents']} 件 / {s['chunks']} 段

下載清單：
{files_str}

以上報告。""", False
        except Exception as e:
            return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

Drive 同步失敗：{e}

請確認：
1. Drive 資料夾已分享給 Service Account
2. Service Account 金鑰檔存在

以上報告。""", False

    if text in {"/文件清單", "文件清單", "/清單"}:
        docs = rag.list_documents()
        if docs:
            doc_list = "\n".join(f"{i+1}. {d}" for i, d in enumerate(docs))
            body = f"目前已索引 {len(docs)} 份文件：\n{doc_list}"
        else:
            body = "資料庫尚無索引文件，請上傳後執行 /重建索引"
        return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

{body}

以上報告。""", False

    if text in {"/說明", "說明", "/help", "help"}:
        return f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

使用說明：

📌 直接輸入問題
例：有什麼水源匱乏地區嗎
例：消防通道有哪些資料

📋 系統指令
/狀態     — 查資料庫狀態
/文件清單 — 查已索引文件
/重建索引 — 重新掃描 data/raw/ 建立索引
/說明     — 顯示此說明

📷 傳送圖片
可直接拍攝公文、表格照片，小秘書會自動辨識並查詢。

以上報告。""", False

    # General query: Codex-first test mode with conversation memory.
    # Keep slash/system commands above deterministic; all normal questions go through Codex.
    with _HISTORY_LOCK:
        history = list(_CHAT_HISTORY.get(user_id, [])) if user_id else []
    reply = rag.codex_answer(text, history=history) or rag.answer(text, history=history)
    if user_id:
        with _HISTORY_LOCK:
            _CHAT_HISTORY[user_id].append((text, reply))
            if len(_CHAT_HISTORY[user_id]) > _HISTORY_MAX:
                _CHAT_HISTORY[user_id] = _CHAT_HISTORY[user_id][-_HISTORY_MAX:]
    return reply, True


@app.get("/", response_class=PlainTextResponse)
def health() -> str:
    return f"ok - {UNIT_NAME}行政小秘書 LINE Bot"


@app.get("/health")
def health_json() -> dict:
    return {"status": "ok", "service": f"{UNIT_NAME}行政小秘書 LINE Bot", "webhook": f"{PUBLIC_BASE_URL}/webhook", **rag.stats()}


@app.get("/admin/allowlist")
def admin_allowlist(x_admin_token: str | None = Header(default=None)) -> dict:
    check_admin(x_admin_token)
    with _ALLOWLIST_LOCK:
        ids = sorted(_load_allowlist())
    return {"count": len(ids), "user_ids": ids}


@app.delete("/admin/allowlist/{user_id}")
def admin_allowlist_remove(user_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    check_admin(x_admin_token)
    with _ALLOWLIST_LOCK:
        ids = _load_allowlist()
        ids.discard(user_id)
        _save_allowlist(ids)
    return {"removed": user_id, "count": len(ids)}


@app.post("/admin/reindex")
def admin_reindex(x_admin_token: str | None = Header(default=None)) -> dict:
    check_admin(x_admin_token)
    return rag.reindex_all(force=True)


MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@app.post("/admin/upload")
async def admin_upload(file: UploadFile = File(...), x_admin_token: str | None = Header(default=None)) -> dict:
    check_admin(x_admin_token)
    filename = Path(file.filename or "upload.bin").name
    suffix = Path(filename).suffix.lower()
    if suffix not in rag.SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {suffix}")
    rag.ensure_dirs()
    target = rag.RAW_DIR / filename
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 50 MB)")
    target.write_bytes(content)
    indexed, message = rag.index_file(target, force=True)
    return {"uploaded": str(target), "indexed": indexed, "message": message, **rag.stats()}


@app.post("/webhook", response_class=PlainTextResponse)
async def webhook(request: Request) -> str:
    signature = request.headers.get("X-Line-Signature", "")
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError as exc:
        raise HTTPException(status_code=400, detail="Invalid LINE signature") from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="LINE webhook handler failed") from exc

    return "OK"


def _start_loading(chat_id: str, stop_event: threading.Event) -> None:
    """背景執行緒：每 55 秒刷新一次 loading 動畫直到 stop_event 被設定。"""
    while not stop_event.is_set():
        try:
            with ApiClient(configuration) as api_client:
                MessagingApi(api_client).show_loading_animation(
                    ShowLoadingAnimationRequest(chatId=chat_id, loadingSeconds=60)
                )
        except Exception:
            pass
        stop_event.wait(55)


def _loading_chat_id(event: MessageEvent) -> str:
    src = event.source
    if hasattr(src, "group_id") and src.group_id:
        return src.group_id
    if hasattr(src, "room_id") and src.room_id:
        return src.room_id
    return src.user_id or ""


def _do_reply(event: MessageEvent, reply_text: str, show_card: bool, card_title: str = "") -> None:
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        messages = split_line_messages(reply_text)
        if show_card:
            messages = [make_summary_card(card_title or "查詢", reply_text=reply_text)] + messages
            messages = messages[:5]
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    user_text = event.message.text
    user_id = getattr(getattr(event, "source", None), "user_id", "") or ""

    # 啟動 loading 動畫（Codex 需要 100 秒，先給用戶回饋）
    chat_id = _loading_chat_id(event)
    stop_loading = threading.Event()
    if chat_id:
        t = threading.Thread(target=_start_loading, args=(chat_id, stop_loading), daemon=True)
        t.start()

    try:
        reply_text, show_card = build_reply(user_text, user_id=user_id)
    except Exception:
        traceback.print_exc()
        reply_text = f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

小秘書查詢時發生系統錯誤，已留下伺服器紀錄，請稍後再試或通知管理者。

以上報告。"""
        show_card = False
    finally:
        stop_loading.set()
    _do_reply(event, reply_text, show_card, card_title=user_text)


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event: MessageEvent) -> None:
    user_id = getattr(getattr(event, "source", None), "user_id", "") or ""
    if user_id and not _is_allowed(user_id):
        _do_reply(event, f"請先輸入啟用密語以使用{BOT_DISPLAY_NAME}。", False)
        return
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            image_bytes = line_bot_api.get_message_content(event.message.id).read()
        extracted = rag.extract_image_text(image_bytes)
        if not extracted:
            reply_text = f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

圖片無法辨識文字，請確認圖片清晰且包含文字內容。

以上報告。"""
            _do_reply(event, reply_text, False)
            return
        # Use extracted text as query; Codex-first test mode.
        query = f"（圖片辨識內容）{extracted[:300]}"
        with _HISTORY_LOCK:
            history = list(_CHAT_HISTORY.get(user_id, [])) if user_id else []
        reply_text = rag.codex_answer(extracted, history=history) or rag.answer(extracted, history=history)
        if user_id:
            with _HISTORY_LOCK:
                _CHAT_HISTORY[user_id].append((query, reply_text))
                if len(_CHAT_HISTORY[user_id]) > _HISTORY_MAX:
                    _CHAT_HISTORY[user_id] = _CHAT_HISTORY[user_id][-_HISTORY_MAX:]
        _do_reply(event, reply_text, True, card_title="圖片文件查詢")
    except Exception:
        traceback.print_exc()
        reply_text = f"""報告人：{BOT_DISPLAY_NAME}
日期：{rag.taiwan_minguo_date()}

圖片處理時發生錯誤，請稍後再試。

以上報告。"""
        _do_reply(event, reply_text, False)
