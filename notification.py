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
        subject = "Journal status monitor test"
        text = (
            "Journal status monitor test email\n"
            "=================================\n"
            f"Generated at: {now}\n"
            f"SMTP: {self.smtp_host}:{self.smtp_port}\n"
            "If you received this message, email notification is configured correctly."
        )
        html_body = f"""
        <h2>Journal status monitor test</h2>
        <p>If you received this message, email notification is configured correctly.</p>
        <p><strong>Generated at:</strong> {html.escape(now)}</p>
        <p><strong>SMTP:</strong> {html.escape(self.smtp_host)}:{self.smtp_port}</p>
        """
        return self._send(subject, text, html_body)

    def send_change_notification(self, changed_manuscripts: List[Dict]) -> bool:
        if not changed_manuscripts:
            print("No status changes to notify.")
            return True
        subject = f"Journal manuscript status changed ({len(changed_manuscripts)})"
        return self._send(
            subject,
            self._generate_change_text(changed_manuscripts),
            self._generate_change_html(changed_manuscripts),
        )

    def send_daily_report(self, all_manuscripts: List[Dict]) -> bool:
        if not all_manuscripts:
            print("No manuscripts available for the daily report.")
            return True
        subject = f"Journal manuscript daily report ({len(all_manuscripts)})"
        return self._send(
            subject,
            self._generate_daily_text(all_manuscripts),
            self._generate_daily_html(all_manuscripts),
        )

    def _send(self, subject: str, text_body: str, html_body: str) -> bool:
        message = MIMEMultipart("alternative")
        message["From"] = Header(f"Journal Status Monitor <{self.sender}>", "utf-8")
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
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; color: #222; line-height: 1.55; max-width: 860px; margin: 0 auto; padding: 24px; }}
    .header {{ background: #0f766e; color: white; padding: 18px 22px; border-radius: 6px; margin-bottom: 18px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 6px 0 0; opacity: .92; }}
    .item {{ border-left: 4px solid #0f766e; background: #f8fafc; padding: 14px; margin: 12px 0; border-radius: 4px; }}
    .title {{ font-weight: 700; margin-bottom: 8px; }}
    .meta {{ color: #475569; font-size: 14px; margin: 4px 0; }}
    .old {{ color: #b91c1c; text-decoration: line-through; }}
    .new {{ color: #047857; font-weight: 700; }}
    .footer {{ color: #64748b; border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 12px; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="header"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>
  {body}
  <div class="footer">Generated at {html.escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}</div>
</body>
</html>"""

    def _generate_change_html(self, manuscripts: List[Dict]) -> str:
        rows = []
        for index, item in enumerate(manuscripts, 1):
            rows.append(
                f"""<div class="item">
  <div class="title">{index}. {html.escape(str(item.get("title", "Untitled")))}</div>
  <div class="meta">Source: {html.escape(str(item.get("source", "")))} | ID: {html.escape(str(item.get("id", "")))}</div>
  <div class="meta">Status: <span class="old">{html.escape(str(item.get("old_status", "")))}</span> -> <span class="new">{html.escape(str(item.get("new_status", "")))}</span></div>
  <div class="meta">Changed at: {html.escape(str(item.get("changed_at", "")))}</div>
  {self._link_html(item.get("url"))}
</div>"""
            )
        return self._page("Journal manuscript status changed", f"{len(manuscripts)} manuscript(s) changed", "\n".join(rows))

    def _generate_daily_html(self, manuscripts: List[Dict]) -> str:
        rows = []
        for index, item in enumerate(manuscripts, 1):
            rows.append(
                f"""<div class="item">
  <div class="title">{index}. {html.escape(str(item.get("title", "Untitled")))}</div>
  <div class="meta">Source: {html.escape(str(item.get("source", "")))} | ID: {html.escape(str(item.get("id", "")))}</div>
  <div class="meta">Current status: <span class="new">{html.escape(str(item.get("status", "")))}</span></div>
  <div class="meta">Last checked: {html.escape(str(item.get("last_checked", "")))}</div>
  {self._link_html(item.get("url"))}
</div>"""
            )
        return self._page("Journal manuscript daily report", f"{len(manuscripts)} manuscript(s) monitored", "\n".join(rows))

    @staticmethod
    def _link_html(url: object) -> str:
        if not url:
            return ""
        safe_url = html.escape(str(url), quote=True)
        return f'<div class="meta"><a href="{safe_url}">Open submission system</a></div>'

    @staticmethod
    def _generate_change_text(manuscripts: List[Dict]) -> str:
        lines = ["Journal manuscript status changed", "=" * 36, ""]
        for index, item in enumerate(manuscripts, 1):
            lines.extend(
                [
                    f"{index}. {item.get('title', 'Untitled')}",
                    f"   Source: {item.get('source', '')}",
                    f"   ID: {item.get('id', '')}",
                    f"   Status: {item.get('old_status', '')} -> {item.get('new_status', '')}",
                    f"   Changed at: {item.get('changed_at', '')}",
                    f"   URL: {item.get('url', '')}",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _generate_daily_text(manuscripts: List[Dict]) -> str:
        lines = ["Journal manuscript daily report", "=" * 34, ""]
        for index, item in enumerate(manuscripts, 1):
            lines.extend(
                [
                    f"{index}. {item.get('title', 'Untitled')}",
                    f"   Source: {item.get('source', '')}",
                    f"   ID: {item.get('id', '')}",
                    f"   Status: {item.get('status', '')}",
                    f"   Last checked: {item.get('last_checked', '')}",
                    f"   URL: {item.get('url', '')}",
                    "",
                ]
            )
        return "\n".join(lines)