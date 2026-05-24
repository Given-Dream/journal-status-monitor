"""Email notification helpers."""
from __future__ import annotations

import html
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from config import Config


class EmailNotifier:
    def __init__(self) -> None:
        self.sender = Config.EMAIL_SENDER
        self.password = Config.EMAIL_PASSWORD
        self.receivers = Config.EMAIL_RECEIVERS
        self.smtp_host, self.smtp_port = Config.get_smtp_config()

    def send_test_email(self) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = "鏈熷垔鐘舵€佺洃鎺ф祴璇曢偖浠?
        text = (
            "鏈熷垔鐘舵€佺洃鎺ф祴璇曢偖浠禱n"
            "====================\n"
            f"鐢熸垚鏃堕棿: {now}\n"
            f"SMTP: {self.smtp_host}:{self.smtp_port}\n"
            "濡傛灉浣犳敹鍒拌繖灏侀偖浠讹紝璇存槑閭欢閫氱煡閰嶇疆宸茬粡鍙敤銆?
        )
        html_body = self._page(
            "鏈熷垔鐘舵€佺洃鎺ф祴璇曢偖浠?,
            "閭欢閫氱煡閰嶇疆宸茬粡鍙敤",
            f"""
            <div class="summary-card">
              <div class="summary-label">娴嬭瘯缁撴灉</div>
              <div class="summary-value">鍙戦€佹垚鍔?/div>
              <p>濡傛灉浣犳敹鍒拌繖灏侀偖浠讹紝璇存槑 GitHub Actions 涓殑閭欢閫氱煡閰嶇疆宸茬粡鐢熸晥銆?/p>
            </div>
            <div class="meta-grid">
              <div><span>鐢熸垚鏃堕棿</span><strong>{html.escape(now)}</strong></div>
              <div><span>SMTP</span><strong>{html.escape(self.smtp_host)}:{self.smtp_port}</strong></div>
            </div>
            """,
        )
        return self._send(subject, text, html_body)

    def send_change_notification(self, changed_manuscripts: List[Dict]) -> bool:
        if not changed_manuscripts:
            print("No status changes to notify.")
            return True
        subject = f"鏈熷垔绋夸欢鐘舵€佹洿鏂伴€氱煡锛坽len(changed_manuscripts)}绡囷級"
        return self._send(
            subject,
            self._generate_change_text(changed_manuscripts),
            self._generate_change_html(changed_manuscripts),
        )

    def send_daily_report(self, all_manuscripts: List[Dict]) -> bool:
        if not all_manuscripts:
            print("No manuscripts available for the daily report.")
            return True
        subject = f"鏈熷垔绋夸欢姣忔棩鐘舵€佹姤鍛婏紙{len(all_manuscripts)}绡囷級"
        return self._send(
            subject,
            self._generate_daily_text(all_manuscripts),
            self._generate_daily_html(all_manuscripts),
        )

    def _send(self, subject: str, text_body: str, html_body: str) -> bool:
        message = MIMEMultipart("alternative")
        message["From"] = Header(f"鏈熷垔鐘舵€佺洃鎺?<{self.sender}>", "utf-8")
        message["To"] = Header(", ".join(self.receivers), "utf-8")
        message["Subject"] = Header(subject, "utf-8")
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            print(f"Sending email to {', '.join(self.receivers)} through {self.smtp_host}:{self.smtp_port}...")
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.sender, self.password)
                    server.sendmail(self.sender, self.receivers, message.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.sender, self.password)
                    server.sendmail(self.sender, self.receivers, message.as_string())
            print("Email sent.")
            return True
        except Exception as exc:
            print(f"Email send failed: {exc}")
            return False

    @staticmethod
    def _page(title: str, subtitle: str, body: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #eef3f1;
      color: #1f2933;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
      line-height: 1.65;
    }}
    .wrap {{
      max-width: 880px;
      margin: 0 auto;
      padding: 28px 16px;
    }}
    .panel {{
      background: #ffffff;
      border: 1px solid #dce7e3;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 14px 36px rgba(15, 82, 76, .10);
    }}
    .hero {{
      background: #0f766e;
      color: #ffffff;
      padding: 28px 32px;
    }}
    .hero h1 {{
      margin: 0;
      font-size: 24px;
      line-height: 1.35;
      font-weight: 760;
    }}
    .hero p {{
      margin: 8px 0 0;
      color: #d7fffa;
      font-size: 15px;
    }}
    .content {{
      padding: 24px 28px 30px;
    }}
    .summary-card {{
      background: #f4faf8;
      border: 1px solid #cfe5df;
      border-radius: 8px;
      padding: 16px 18px;
      margin-bottom: 18px;
    }}
    .summary-label {{
      color: #52706b;
      font-size: 13px;
      letter-spacing: .02em;
    }}
    .summary-value {{
      margin-top: 4px;
      color: #0f766e;
      font-size: 22px;
      font-weight: 760;
    }}
    .item {{
      border: 1px solid #dfe8e5;
      border-left: 5px solid #0f766e;
      background: #fbfdfc;
      padding: 18px 18px 16px;
      margin: 14px 0;
      border-radius: 8px;
    }}
    .title {{
      color: #111827;
      font-size: 16px;
      font-weight: 740;
      margin-bottom: 12px;
    }}
    .meta {{
      color: #42526a;
      font-size: 14px;
      margin: 6px 0;
    }}
    .label {{
      color: #6b7a90;
      display: inline-block;
      min-width: 72px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e6f4f1;
      color: #0f766e;
      font-size: 12px;
      font-weight: 700;
      vertical-align: middle;
    }}
    .status {{
      color: #047857;
      font-weight: 760;
    }}
    .old {{
      color: #b42318;
      text-decoration: line-through;
    }}
    .new {{
      color: #047857;
      font-weight: 760;
    }}
    .button {{
      display: inline-block;
      margin-top: 10px;
      padding: 8px 12px;
      color: #ffffff !important;
      background: #0f766e;
      text-decoration: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 700;
    }}
    .meta-grid {{
      display: block;
      margin-top: 16px;
    }}
    .meta-grid div {{
      background: #f8fbfa;
      border: 1px solid #e0ebe8;
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 10px;
    }}
    .meta-grid span {{
      display: block;
      color: #6b7a90;
      font-size: 13px;
    }}
    .meta-grid strong {{
      display: block;
      color: #1f2933;
      margin-top: 3px;
      word-break: break-word;
    }}
    .footer {{
      color: #73837f;
      border-top: 1px solid #e4ece9;
      margin-top: 24px;
      padding-top: 14px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="hero">
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(subtitle)}</p>
      </div>
      <div class="content">
        {body}
        <div class="footer">鏈偖浠剁敱鏈熷垔鐘舵€佺洃鎺х▼搴忚嚜鍔ㄥ彂閫併€傜敓鎴愭椂闂达細{html.escape(now)}</div>
      </div>
    </div>
  </div>
</body>
</html>"""

    def _generate_change_html(self, manuscripts: List[Dict]) -> str:
        rows = []
        for index, item in enumerate(manuscripts, 1):
            rows.append(
                f"""<div class="item">
  <div class="title">{index}. {html.escape(str(item.get("title", "Untitled")))}</div>
  <div class="meta"><span class="label">鏉ユ簮</span><span class="badge">{html.escape(str(item.get("source", "")))}</span></div>
  <div class="meta"><span class="label">绋夸欢 ID</span>{html.escape(str(item.get("id", "")))}</div>
  <div class="meta"><span class="label">鐘舵€佸彉鍖?/span><span class="old">{html.escape(str(item.get("old_status", "")))}</span> -> <span class="new">{html.escape(str(item.get("new_status", "")))}</span></div>
  <div class="meta"><span class="label">鍙樺寲鏃堕棿</span>{html.escape(str(item.get("changed_at", "")))}</div>
  {self._link_html(item.get("url"))}
</div>"""
            )
        return self._page("鏈熷垔绋夸欢鐘舵€佹洿鏂伴€氱煡", f"妫€娴嬪埌 {len(manuscripts)} 绡囩浠剁姸鎬佸彂鐢熷彉鍖?, "\n".join(rows))

    def _generate_daily_html(self, manuscripts: List[Dict]) -> str:
        rows = []
        for index, item in enumerate(manuscripts, 1):
            rows.append(
                f"""<div class="item">
  <div class="title">{index}. {html.escape(str(item.get("title", "Untitled")))}</div>
  <div class="meta"><span class="label">鏉ユ簮</span><span class="badge">{html.escape(str(item.get("source", "")))}</span></div>
  <div class="meta"><span class="label">绋夸欢 ID</span>{html.escape(str(item.get("id", "")))}</div>
  <div class="meta"><span class="label">褰撳墠鐘舵€?/span><span class="status">{html.escape(str(item.get("status", "")))}</span></div>
  <div class="meta"><span class="label">妫€鏌ユ椂闂?/span>{html.escape(str(item.get("last_checked", "")))}</div>
  {self._link_html(item.get("url"))}
</div>"""
            )
        return self._page("鏈熷垔绋夸欢姣忔棩鐘舵€佹姤鍛?, f"褰撳墠鐩戞帶 {len(manuscripts)} 绡囩浠?, "\n".join(rows))

    @staticmethod
    def _link_html(url: object) -> str:
        if not url:
            return ""
        safe_url = html.escape(str(url), quote=True)
        return f'<a class="button" href="{safe_url}">鎵撳紑鎶曠绯荤粺</a>'

    @staticmethod
    def _generate_change_text(manuscripts: List[Dict]) -> str:
        lines = ["鏈熷垔绋夸欢鐘舵€佹洿鏂伴€氱煡", "=" * 28, ""]
        for index, item in enumerate(manuscripts, 1):
            lines.extend(
                [
                    f"{index}. {item.get('title', 'Untitled')}",
                    f"   鏉ユ簮: {item.get('source', '')}",
                    f"   绋夸欢 ID: {item.get('id', '')}",
                    f"   鐘舵€佸彉鍖? {item.get('old_status', '')} -> {item.get('new_status', '')}",
                    f"   鍙樺寲鏃堕棿: {item.get('changed_at', '')}",
                    f"   鎶曠绯荤粺: {item.get('url', '')}",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _generate_daily_text(manuscripts: List[Dict]) -> str:
        lines = ["鏈熷垔绋夸欢姣忔棩鐘舵€佹姤鍛?, "=" * 26, ""]
        for index, item in enumerate(manuscripts, 1):
            lines.extend(
                [
                    f"{index}. {item.get('title', 'Untitled')}",
                    f"   鏉ユ簮: {item.get('source', '')}",
                    f"   绋夸欢 ID: {item.get('id', '')}",
                    f"   褰撳墠鐘舵€? {item.get('status', '')}",
                    f"   妫€鏌ユ椂闂? {item.get('last_checked', '')}",
                    f"   鎶曠绯荤粺: {item.get('url', '')}",
                    "",
                ]
            )
        return "\n".join(lines)