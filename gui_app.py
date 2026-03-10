import customtkinter as ctk
import threading
import queue
import asyncio
import time
import os
import collections
from datetime import datetime, timedelta

import config_manager
from logger import logger, log_queue, LOG_FILE
import task_manager
import get_token
import channel_sweep
import liked_cache
import requests
import web_panel

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

ARTICLE_DETAIL_URL = "https://tbeanews.tbea.com/api/article/detail"

# 扫描范围预设
def _last_month_range():
    now = datetime.now()
    first_this = now.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    return first_prev.strftime("%Y-%m-%d"), last_prev.strftime("%Y-%m-%d")

SCAN_PRESETS = {
    "今天": lambda: (datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")),
    "昨天": lambda: ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                      (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")),
    "最近3天": lambda: ((datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                        datetime.now().strftime("%Y-%m-%d")),
    "本周": lambda: ((datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d"),
                     datetime.now().strftime("%Y-%m-%d")),
    "本月": lambda: (datetime.now().strftime("%Y-%m-01"), datetime.now().strftime("%Y-%m-%d")),
    "上月": _last_month_range,
    "自定义": None,
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("E+ 新闻点赞工具 v2.0.0")
        self.geometry("1050x720")
        self.minsize(850, 580)

        self.scheduler = task_manager.TaskManager()
        self.auto_mode_running = False
        self.scan_stop_event = threading.Event()
        self.scan_thread = None
        self._token_valid = None
        config_manager.ensure_config_exists()

        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._init_app()

    # ============================================================
    #  SIDEBAR
    # ============================================================
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=["#f7f7f8", "#16162a"])
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        self.sidebar = sb

        # 1) Logo
        ctk.CTkLabel(sb, text="⚡ E+ 点赞", font=ctk.CTkFont(size=22, weight="bold")
                      ).pack(pady=(30, 2))
        ctk.CTkLabel(sb, text="自动新闻点赞工具", font=ctk.CTkFont(size=11),
                      text_color=["#888", "#666"]).pack(pady=(0, 20))

        # 2) 账号
        af = ctk.CTkFrame(sb, fg_color="transparent")
        af.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkLabel(af, text="👤", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 4))
        self.account_selector = ctk.CTkOptionMenu(
            af, values=["加载中..."], width=135, height=26,
            font=ctk.CTkFont(size=11), command=self._on_account_switch)
        self.account_selector.pack(side="left")

        # 3) 状态
        self.status_badge = ctk.CTkLabel(
            sb, text="⚪ 空闲", font=ctk.CTkFont(size=12), text_color=["#777", "#888"])
        self.status_badge.pack(pady=(2, 16))

        # 分隔线
        self._divider(sb)

        # 4) 自动挂机（主要操作）
        self.auto_btn = ctk.CTkButton(
            sb, text="🚀 启动自动挂机", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_auto_mode)
        self.auto_btn.pack(fill="x", padx=16, pady=(12, 4))

        # 停止按钮（动态显示）
        self.stop_btn = ctk.CTkButton(
            sb, text="⏹ 停止", height=32,
            fg_color="#dc2626", hover_color="#991b1b",
            font=ctk.CTkFont(size=12), command=self.stop_current_scan)
        # 不 pack，初始隐藏

        self._divider(sb)

        # 5) 工具按钮（扁平风格）
        for text, cmd in [
            ("⚙️  设置", self.open_settings),
            ("📊  导出月报", self.run_export_report_async),
        ]:
            ctk.CTkButton(
                sb, text=text, height=30, anchor="w",
                fg_color="transparent", text_color=["#444", "#bbb"],
                hover_color=["#e8e8e8", "#2a2a40"],
                font=ctk.CTkFont(size=12), command=cmd
            ).pack(fill="x", padx=16, pady=1)

        # 底部弹簧 + 主题
        spacer = ctk.CTkFrame(sb, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.theme_menu = ctk.CTkOptionMenu(
            sb, values=["System", "Dark", "Light"], width=130, height=24,
            font=ctk.CTkFont(size=10),
            command=lambda v: ctk.set_appearance_mode(v))
        self.theme_menu.pack(pady=(0, 16))

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=["#e0e0e0", "#2a2a40"]).pack(fill="x", padx=16, pady=8)

    # ============================================================
    #  MAIN
    # ============================================================
    def _build_main(self):
        m = ctk.CTkFrame(self, fg_color="transparent")
        m.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        m.grid_columnconfigure(0, weight=1)
        m.grid_rowconfigure(2, weight=1)  # 日志区伸缩
        self.main_frame = m

        # ---- ROW 0: 统计卡片 ----
        cg = ctk.CTkFrame(m, fg_color="transparent")
        cg.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        cg.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total  = self._card(cg, 0, "本月文章", "---",  "#60a5fa")
        self.card_liked  = self._card(cg, 1, "已点赞",   "---",  "#4ade80")
        self.card_last   = self._card(cg, 2, "上次扫描", "---",  "#a78bfa")
        self.card_token  = self._card(cg, 3, "Token",    "检测中", "#fb923c")

        # ---- ROW 1: 扫描面板 ----
        sp = ctk.CTkFrame(m, corner_radius=12)
        sp.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        # 用一个内部容器让内容居中 + 整齐
        inner = ctk.CTkFrame(sp, fg_color="transparent")
        inner.pack(padx=16, pady=14)

        # 上排: 预设 + 按钮
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(top_row, text="扫描范围",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 10))

        self.preset_menu = ctk.CTkOptionMenu(
            top_row, values=list(SCAN_PRESETS.keys()),
            width=130, height=32, font=ctk.CTkFont(size=12),
            command=self._on_preset_change)
        self.preset_menu.set("本月")
        self.preset_menu.pack(side="left", padx=(0, 12))

        self.scan_btn = ctk.CTkButton(
            top_row, text="▶  开始扫描", width=130, height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669", hover_color="#047857",
            command=self._do_scan)
        self.scan_btn.pack(side="left")

        # 下排: 自定义日期输入 (初始隐藏)
        self.custom_row = ctk.CTkFrame(inner, fg_color="transparent")
        # 不 pack，初始隐藏
        cf = self.custom_row
        ctk.CTkLabel(cf, text="从", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=(0, 4))
        self.sd_entry = ctk.CTkEntry(cf, placeholder_text="2026-03-01", width=120, height=28)
        self.sd_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(cf, text="到", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=(0, 4))
        self.ed_entry = ctk.CTkEntry(cf, placeholder_text="2026-03-10", width=120, height=28)
        self.ed_entry.pack(side="left")

        # ---- ROW 2: 日志 ----
        log_wrap = ctk.CTkFrame(m, fg_color="transparent")
        log_wrap.grid(row=2, column=0, sticky="nsew")
        log_wrap.grid_columnconfigure(0, weight=1)
        log_wrap.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(log_wrap, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="运行日志",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="清空", width=50, height=22, corner_radius=6,
                      fg_color="transparent", text_color=["#aaa", "#555"],
                      hover_color=["#eee", "#333"], font=ctk.CTkFont(size=11),
                      command=self.clear_logs).grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(
            log_wrap, state="disabled", wrap="word", corner_radius=10,
            font=ctk.CTkFont(family="Menlo", size=12))
        self.log_textbox.grid(row=1, column=0, sticky="nsew")
        self.log_textbox.tag_config("WARNING", foreground="#D2691E")
        self.log_textbox.tag_config("ERROR", foreground="#ef4444")

    # ============================================================
    #  卡片工厂
    # ============================================================
    def _card(self, parent, col, title, value, color):
        c = ctk.CTkFrame(parent, corner_radius=10)
        c.grid(row=0, column=col, padx=5, sticky="ew")
        ctk.CTkLabel(c, text=title, font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(10, 2))
        vl = ctk.CTkLabel(c, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=color)
        vl.pack(pady=(0, 10))
        return vl

    # ============================================================
    #  初始化
    # ============================================================
    def _init_app(self):
        self._load_recent_logs()
        self.after(100, self.poll_logs)
        self.after(5000, self._token_health_tick)
        self._refresh_status()
        self._refresh_stats()

        logger.info("=========================================")
        logger.info("  ⚡ E+ 自动点赞工具 v2.0.0 已启动")
        logger.info(f"  📦 本地缓存: {liked_cache.get_cache_size()} 篇已赞记录")
        logger.info("=========================================")

        threading.Thread(target=self._initial_checks, daemon=True).start()
        web_panel.set_gui_app(self)
        web_panel.start_web_panel(port=5050)

    def _initial_checks(self):
        token = config_manager.get_token()
        if not token:
            logger.warning("首次使用，请先前往 ⚙️ 设置 配置账号。")
            return
        try:
            r = requests.get(ARTICLE_DETAIL_URL, headers={"token": token},
                             params={'id': 8141}, timeout=10)
            if r.json().get("code") == 1:
                logger.info("✅ Token 有效。")
                self._token_valid = True
                self.after(0, lambda: self.card_token.configure(text="✅ 有效", text_color="#4ade80"))
            else:
                logger.warning("⚠️ Token 已过期。")
                self._token_valid = False
                self.after(0, lambda: self.card_token.configure(text="❌ 过期", text_color="#f87171"))
        except:
            logger.warning("⚠️ 网络异常。")

    def _load_recent_logs(self):
        if not os.path.exists(LOG_FILE):
            return
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = collections.deque(f, maxlen=150)
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", "─── 历史日志 ───\n", "WARNING")
            for line in lines:
                line = line.rstrip('\n')
                tag = "INFO"
                if "[WARNING]" in line: tag = "WARNING"
                if "[ERROR]" in line: tag = "ERROR"
                parts = line.split(" - ", 2)
                if len(parts) >= 3:
                    t = parts[0].split(" ")[-1] if " " in parts[0] else parts[0]
                    display = f"[{t}] {parts[2]}"
                else:
                    display = line
                self.log_textbox.insert("end", display + "\n", tag)
            self.log_textbox.insert("end", "─── 结束 ───\n\n", "WARNING")
            self.log_textbox.configure(state="disabled")
            self.log_textbox.see("end")
        except:
            pass

    # ============================================================
    #  Token 健康
    # ============================================================
    def _token_health_tick(self):
        def check():
            token = config_manager.get_token()
            if not token:
                self.after(0, lambda: self.card_token.configure(text="未设置", text_color="gray"))
                return
            try:
                r = requests.get(ARTICLE_DETAIL_URL, headers={"token": token},
                                 params={'id': 8141}, timeout=10)
                ok = r.json().get("code") == 1
                self._token_valid = ok
                if ok:
                    self.after(0, lambda: self.card_token.configure(text="✅ 有效", text_color="#4ade80"))
                else:
                    self.after(0, lambda: self.card_token.configure(text="❌ 过期", text_color="#f87171"))
            except:
                self.after(0, lambda: self.card_token.configure(text="⚠️ 未知", text_color="#fb923c"))
        threading.Thread(target=check, daemon=True).start()
        self.after(300000, self._token_health_tick)

    # ============================================================
    #  统计
    # ============================================================
    def _refresh_stats(self):
        stats = config_manager.get_sweep_stats()
        total = stats.get("total", 0)
        liked = stats.get("liked", 0)
        skipped = stats.get("skipped", 0)
        missed = total - skipped - liked if total > 0 else 0

        self.card_total.configure(text=str(total) if total else "---")
        self.card_liked.configure(text=str(skipped + liked) if total else "---")
        
        # 上次扫描时间
        last_time = stats.get("last_sweep_time", "")
        if last_time:
            try:
                dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - dt
                mins = int(delta.total_seconds() / 60)
                if mins < 1:
                    ago = "刚刚"
                elif mins < 60:
                    ago = f"{mins}分钟前"
                elif mins < 1440:
                    ago = f"{mins // 60}小时前"
                else:
                    ago = f"{mins // 1440}天前"
                self.card_last.configure(text=ago)
            except:
                self.card_last.configure(text=last_time[:10])
        else:
            self.card_last.configure(text="从未")

    # ============================================================
    #  状态管理
    # ============================================================
    def _refresh_status(self):
        accs = config_manager.get_all_accounts()
        ai = config_manager.get_active_account_index()
        if accs:
            names = [a["username"] for a in accs]
            self.account_selector.configure(values=names)
            if 0 <= ai < len(names): self.account_selector.set(names[ai])
        else:
            self.account_selector.configure(values=["未设置"])
            self.account_selector.set("未设置")

        if self.auto_mode_running:
            self.status_badge.configure(text="🟢 自动运行中", text_color="#4ade80")
            self.auto_btn.configure(text="⏹ 停止挂机", fg_color="#dc2626", hover_color="#991b1b")
        else:
            self.status_badge.configure(text="⚪ 空闲", text_color=["#777", "#888"])
            self.auto_btn.configure(text="🚀 启动自动挂机",
                                     fg_color=["#3B8ED0", "#1F6AA5"],
                                     hover_color=["#36719F", "#144870"])

    def _show_stop(self):
        self.stop_btn.pack(fill="x", padx=16, pady=(0, 4), after=self.auto_btn)

    def _hide_stop(self):
        self.stop_btn.pack_forget()

    def _set_scanning(self, active: bool):
        st = "disabled" if active else "normal"
        self.scan_btn.configure(state=st, text="⏳ 扫描中..." if active else "▶  开始扫描")
        self.preset_menu.configure(state=st)
        self.export_btn = None  # handled in sidebar
        if active:
            self._show_stop()
        else:
            self._hide_stop()

    # ============================================================
    #  事件
    # ============================================================
    def _on_preset_change(self, value):
        if value == "自定义":
            self.custom_row.pack(fill="x", pady=(8, 0))
        else:
            self.custom_row.pack_forget()

    def _on_account_switch(self, selected):
        for a in config_manager.get_all_accounts():
            if a["username"] == selected:
                config_manager.switch_account(a["index"])
                self._refresh_stats()
                self._refresh_status()
                logger.info(f"🔀 切换账号: {selected}")
                break

    def stop_current_scan(self):
        logger.info("⏹️ 停止请求已发送...")
        self.scan_stop_event.set()

    def poll_logs(self):
        try:
            while True:
                lv, msg = log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                tag = {"WARNING": "WARNING", "ERROR": "ERROR"}.get(lv, "INFO")
                self.log_textbox.insert("end", msg + "\n", tag)
                self.log_textbox.configure(state="disabled")
                self.log_textbox.see("end")
        except queue.Empty:
            pass
        self.after(100, self.poll_logs)

    def clear_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    # ============================================================
    #  扫描
    # ============================================================
    def _get_date_range(self):
        preset = self.preset_menu.get()
        fn = SCAN_PRESETS.get(preset)
        if fn is not None:
            return fn()
        # 自定义
        sd, ed = self.sd_entry.get().strip(), self.ed_entry.get().strip()
        for d, lab in [(sd, "起始"), (ed, "结束")]:
            if not d:
                logger.error(f"❌ 请输入{lab}日期"); return None
            try: datetime.strptime(d, "%Y-%m-%d")
            except: logger.error(f"❌ {lab}日期格式错误"); return None
        if sd > ed:
            logger.error("❌ 起始不能晚于结束"); return None
        return sd, ed

    def _do_scan(self):
        dr = self._get_date_range()
        if not dr: return
        self._set_scanning(True)
        self.scan_thread = threading.Thread(target=self._sweep_worker, args=dr, daemon=True)
        self.scan_thread.start()

    def _sweep_worker(self, start_date=None, end_date=None):
        self.scan_stop_event.clear()
        desc = f"{start_date} ~ {end_date}" if start_date else "本月"
        logger.info(f"\n{'='*40}")
        logger.info(f"  📡 频道扫描: {desc}")
        logger.info(f"{'='*40}")

        token = config_manager.get_token()
        cookies = config_manager.get_ejia_cookies()
        if not token or not cookies:
            logger.warning("凭据缺失，启动登录...")
            if not self._run_token_flow():
                logger.error("登录失败。")
                self.after(0, lambda: self._set_scanning(False))
                return

        total, liked, skipped = channel_sweep.run_sweep(start_date, end_date, self.scan_stop_event)

        if total == -1:
            logger.info("🔄 Session 过期，刷新中...")
            if self._run_token_flow():
                channel_sweep.run_sweep(start_date, end_date, self.scan_stop_event)
            else:
                logger.error("❌ 刷新失败。")

        self.after(0, self._refresh_stats)
        self.after(0, lambda: self._set_scanning(False))

    def _run_token_flow(self) -> bool:
        username, password = config_manager.get_credentials()
        if not username or not password:
            logger.error("❌ 请先配置账号。"); return False
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(get_token.get_new_token(username, password))
        loop.close()
        if data:
            config_manager.save_token(data)
            logger.info("✅ 凭据已更新。")
            self._token_valid = True
            self.after(0, lambda: self.card_token.configure(text="✅ 有效", text_color="#4ade80"))
            return True
        logger.error("❌ 凭据获取失败。"); return False

    def _keep_session_alive(self):
        cookies = config_manager.get_ejia_cookies()
        if not cookies: return
        try:
            r = requests.post("https://ejia.tbea.com/space/c/rest/user/checkLogin",
                              cookies=cookies, headers={"Content-Length": "0"}, timeout=10)
            if r.status_code != 200:
                logger.warning(f"⚠️ 心跳异常: {r.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ 心跳失败: {e}")

    # ============================================================
    #  导出
    # ============================================================
    def run_export_report_async(self):
        def worker():
            import report_exporter
            logger.info("\n📊 导出月度报告...")
            fp = report_exporter.export_monthly_report(self.scan_stop_event)
            if fp: logger.info(f"📊 已生成: {fp}")
            else: logger.warning("⚠️ 导出失败。")
        threading.Thread(target=worker, daemon=True).start()

    # ============================================================
    #  自动挂机
    # ============================================================
    def toggle_auto_mode(self):
        if self.auto_mode_running:
            self.auto_mode_running = False
            self.scan_stop_event.set()
            self.scheduler.stop()
            self.scheduler.tasks.clear()
            self._hide_stop()
            self._set_scanning(False)
            self._refresh_status()
        else:
            self.auto_mode_running = True
            sh, th = config_manager.get_intervals()
            self.scheduler.add_task(
                lambda: self._sweep_worker(
                    datetime.now().strftime("%Y-%m-01"),
                    datetime.now().strftime("%Y-%m-%d")),
                sh, "频道扫描")
            self.scheduler.add_task(self._run_token_flow, th, "Token刷新", initial_delay_hr=th)
            self.scheduler.add_task(self._keep_session_alive, 5.0/60.0, "心跳保活")
            self.scheduler.start()
            self._refresh_status()
            self._set_scanning(True)
            self.scan_thread = threading.Thread(target=self._sweep_worker, daemon=True)
            self.scan_thread.start()

    # ============================================================
    #  Web 面板 API 接口
    # ============================================================
    def remote_scan_today(self):
        t = datetime.now().strftime("%Y-%m-%d")
        self.after(0, lambda: self._set_scanning(True))
        threading.Thread(target=self._sweep_worker, args=(t, t), daemon=True).start()

    def remote_scan_month(self):
        sd = datetime.now().strftime("%Y-%m-01")
        ed = datetime.now().strftime("%Y-%m-%d")
        self.after(0, lambda: self._set_scanning(True))
        threading.Thread(target=self._sweep_worker, args=(sd, ed), daemon=True).start()

    # ============================================================
    #  设置
    # ============================================================
    def open_settings(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("⚙️ 设置")
        dlg.geometry("460x620")
        dlg.grab_set()

        sf = ctk.CTkScrollableFrame(dlg, width=420)
        sf.pack(fill="both", expand=True, padx=10, pady=10)

        # 当前账号
        self._sec(sf, "👤 当前账号")
        un, pw = config_manager.get_credentials()
        ue = ctk.CTkEntry(sf, placeholder_text="工号", width=260)
        ue.pack(anchor="w", padx=12, pady=2)
        if un: ue.insert(0, un)
        pe = ctk.CTkEntry(sf, placeholder_text="密码", show="*", width=260)
        pe.pack(anchor="w", padx=12, pady=2)
        if pw: pe.insert(0, pw)

        # 添加账号
        self._sec(sf, "➕ 添加账号")
        aaf = ctk.CTkFrame(sf, fg_color="transparent")
        aaf.pack(fill="x", padx=12, pady=2)
        nue = ctk.CTkEntry(aaf, placeholder_text="工号", width=110)
        nue.pack(side="left", padx=(0,3))
        npe = ctk.CTkEntry(aaf, placeholder_text="密码", show="*", width=110)
        npe.pack(side="left", padx=(0,5))
        alf = ctk.CTkFrame(sf); alf.pack(fill="x", padx=12, pady=4)

        def _ral():
            for w in alf.winfo_children(): w.destroy()
            accs = config_manager.get_all_accounts()
            ai = config_manager.get_active_account_index()
            for a in accs:
                r = ctk.CTkFrame(alf, fg_color="transparent"); r.pack(fill="x", pady=1)
                p = "✅ " if a["index"]==ai else "    "
                ctk.CTkLabel(r, text=f"{p}{a['username']}", anchor="w").pack(side="left", padx=4)
                if len(accs)>1:
                    def mk(i):
                        def d(): config_manager.remove_account(i); self._refresh_status(); _ral()
                        return d
                    ctk.CTkButton(r, text="✕", width=26, height=20, fg_color="#dc2626",
                                hover_color="#991b1b", command=mk(a["index"])).pack(side="right", padx=4)

        def _add():
            a,b = nue.get().strip(), npe.get().strip()
            if a and b:
                config_manager.add_account(a,b)
                nue.delete(0,"end"); npe.delete(0,"end")
                self._refresh_status(); _ral()
        ctk.CTkButton(aaf, text="添加", width=50, height=26, command=_add).pack(side="left")
        _ral()

        # 频率
        self._sec(sf, "⏱️ 频率（小时）")
        frf = ctk.CTkFrame(sf, fg_color="transparent")
        frf.pack(fill="x", padx=12, pady=2)
        shr, thr = config_manager.get_intervals()
        ctk.CTkLabel(frf, text="扫描:").pack(side="left")
        se = ctk.CTkEntry(frf, width=45); se.pack(side="left", padx=3); se.insert(0, str(shr))
        ctk.CTkLabel(frf, text=" Token:").pack(side="left")
        te = ctk.CTkEntry(frf, width=45); te.pack(side="left", padx=3); te.insert(0, str(thr))

        # 频道
        self._sec(sf, "📡 目标频道")
        chs = config_manager.get_channels()
        clf = ctk.CTkFrame(sf); clf.pack(fill="x", padx=12, pady=4)

        def _rcl():
            for w in clf.winfo_children(): w.destroy()
            for i, c in enumerate(chs):
                r = ctk.CTkFrame(clf, fg_color="transparent"); r.pack(fill="x", pady=1)
                ctk.CTkLabel(r, text=f"  {c['name']}", anchor="w", width=170).pack(side="left")
                def mk(j):
                    def d(): chs.pop(j); _rcl()
                    return d
                ctk.CTkButton(r, text="✕", width=26, height=20, fg_color="#dc2626",
                            hover_color="#991b1b", command=mk(i)).pack(side="right", padx=4)
        _rcl()
        caf = ctk.CTkFrame(sf, fg_color="transparent"); caf.pack(fill="x", padx=12, pady=2)
        cne = ctk.CTkEntry(caf, placeholder_text="名称", width=100); cne.pack(side="left", padx=(0,3))
        cie = ctk.CTkEntry(caf, placeholder_text="XT-xxx-xxx", width=170); cie.pack(side="left", padx=(0,5))
        def _ach():
            n,d = cne.get().strip(), cie.get().strip()
            if n and d: chs.append({"name":n,"id":d}); cne.delete(0,"end"); cie.delete(0,"end"); _rcl()
        ctk.CTkButton(caf, text="➕", width=36, height=26, command=_ach).pack(side="left")

        # 保存
        def save():
            try:
                config_manager.update_credentials(ue.get(), pe.get())
                config_manager.save_intervals(float(se.get()), float(te.get()))
                config_manager.save_channels(chs)
                self._refresh_status(); self._refresh_stats()
                logger.info("⚙️ 已保存！"); dlg.destroy()
            except ValueError: logger.error("❌ 频率须为数字")
        ctk.CTkButton(sf, text="💾 保存", height=34, font=ctk.CTkFont(weight="bold"), command=save).pack(pady=14)

    def _sec(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(anchor="w", padx=12, pady=(12, 2))


if __name__ == "__main__":
    app = App()
    app.mainloop()
