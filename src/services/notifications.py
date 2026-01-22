"""Notification service for Slack and email alerts."""

import logging
from enum import Enum
from typing import Any

import httpx

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""

    REPORT_READY = "report_ready"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    PERFORMANCE_ALERT = "performance_alert"
    BUDGET_ALERT = "budget_alert"
    SYSTEM_ALERT = "system_alert"


class NotificationService:
    """Service for sending notifications via Slack and email."""

    def __init__(self, settings: Settings | None = None):
        """Initialize notification service.

        Args:
            settings: Application settings.
        """
        self._settings = settings or get_settings()

    async def send_slack(
        self,
        message: str,
        channel: str | None = None,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Send a Slack notification.

        Args:
            message: Message text.
            channel: Slack channel (uses webhook default if not specified).
            notification_type: Type of notification.
            details: Additional details to include.

        Returns:
            True if sent successfully.
        """
        if not self._settings.slack_configured:
            logger.warning("Slack is not configured, skipping notification")
            return False

        # Build Slack message blocks
        blocks = self._build_slack_blocks(message, notification_type, details)

        payload = {
            "text": message,
            "blocks": blocks,
        }

        if channel:
            payload["channel"] = channel

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0,
                )

            if response.status_code == 200:
                logger.info(f"Slack notification sent: {notification_type.value}")
                return True
            else:
                logger.error(
                    f"Slack notification failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return False

    def _build_slack_blocks(
        self,
        message: str,
        notification_type: NotificationType,
        details: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Build Slack block kit message.

        Args:
            message: Main message.
            notification_type: Type of notification.
            details: Additional details.

        Returns:
            List of Slack blocks.
        """
        # Icon and color based on type
        icons = {
            NotificationType.REPORT_READY: ":page_facing_up:",
            NotificationType.SYNC_COMPLETED: ":white_check_mark:",
            NotificationType.SYNC_FAILED: ":x:",
            NotificationType.PERFORMANCE_ALERT: ":chart_with_upwards_trend:",
            NotificationType.BUDGET_ALERT: ":moneybag:",
            NotificationType.SYSTEM_ALERT: ":warning:",
        }

        icon = icons.get(notification_type, ":bell:")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{notification_type.value.replace('_', ' ').title()}*\n{message}",
                },
            }
        ]

        # Add details if provided
        if details:
            fields = []
            for key, value in list(details.items())[:10]:  # Limit fields
                fields.append(
                    {
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{value}",
                    }
                )

            if fields:
                blocks.append({"type": "section", "fields": fields[:8]})  # Slack limit

        # Add divider
        blocks.append({"type": "divider"})

        # Add context
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":robot_face: Marketing GraphRAG | {notification_type.value}",
                    }
                ],
            }
        )

        return blocks

    async def send_email(
        self,
        to_emails: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send an email notification via SendGrid.

        Args:
            to_emails: Recipient email addresses.
            subject: Email subject.
            body: Plain text body.
            html_body: HTML body (optional).
            attachments: List of attachments.

        Returns:
            True if sent successfully.
        """
        if not self._settings.email_configured:
            logger.warning("Email is not configured, skipping notification")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import (
                Attachment,
                Content,
                Email,
                Mail,
                To,
            )

            message = Mail(
                from_email=Email(self._settings.SENDGRID_FROM_EMAIL),
                to_emails=[To(email) for email in to_emails],
                subject=subject,
            )

            # Add content
            message.add_content(Content("text/plain", body))
            if html_body:
                message.add_content(Content("text/html", html_body))

            # Add attachments
            if attachments:
                for att in attachments:
                    attachment = Attachment()
                    attachment.file_content = att.get("content")
                    attachment.file_type = att.get("type", "application/octet-stream")
                    attachment.file_name = att.get("filename")
                    attachment.disposition = "attachment"
                    message.add_attachment(attachment)

            # Send
            sg = SendGridAPIClient(self._settings.SENDGRID_API_KEY)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent to {len(to_emails)} recipients: {subject}")
                return True
            else:
                logger.error(f"Email failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Email error: {e}")
            return False

    async def notify_report_ready(
        self,
        client_name: str,
        report_type: str,
        download_url: str,
        recipients: list[str] | None = None,
        slack_channel: str | None = None,
    ) -> dict[str, bool]:
        """Send notification that a report is ready.

        Args:
            client_name: Client name.
            report_type: Type of report.
            download_url: URL to download the report.
            recipients: Email recipients.
            slack_channel: Slack channel.

        Returns:
            Dictionary with notification results.
        """
        message = f"Your {report_type} report for {client_name} is ready for download."

        results = {}

        # Send Slack notification
        if self._settings.slack_configured:
            results["slack"] = await self.send_slack(
                message=message,
                channel=slack_channel,
                notification_type=NotificationType.REPORT_READY,
                details={
                    "Client": client_name,
                    "Report Type": report_type,
                    "Download": f"<{download_url}|Click to download>",
                },
            )

        # Send email notification
        if recipients and self._settings.email_configured:
            html_body = f"""
            <h2>Report Ready</h2>
            <p>{message}</p>
            <p><a href="{download_url}">Download Report</a></p>
            <hr>
            <p style="color: #666; font-size: 12px;">Marketing GraphRAG</p>
            """
            results["email"] = await self.send_email(
                to_emails=recipients,
                subject=f"Report Ready: {client_name} {report_type}",
                body=message,
                html_body=html_body,
            )

        return results

    async def notify_sync_completed(
        self,
        client_name: str,
        platform: str,
        campaigns_synced: int,
        metrics_synced: int,
    ) -> bool:
        """Send notification that data sync completed.

        Args:
            client_name: Client name.
            platform: Platform synced.
            campaigns_synced: Number of campaigns.
            metrics_synced: Number of metric records.

        Returns:
            True if notification sent.
        """
        return await self.send_slack(
            message=f"Data sync completed for {client_name}",
            notification_type=NotificationType.SYNC_COMPLETED,
            details={
                "Platform": platform,
                "Campaigns": str(campaigns_synced),
                "Metrics": str(metrics_synced),
            },
        )

    async def notify_sync_failed(
        self,
        client_name: str,
        platform: str,
        error_message: str,
    ) -> bool:
        """Send notification that data sync failed.

        Args:
            client_name: Client name.
            platform: Platform that failed.
            error_message: Error details.

        Returns:
            True if notification sent.
        """
        return await self.send_slack(
            message=f"Data sync failed for {client_name}",
            notification_type=NotificationType.SYNC_FAILED,
            details={
                "Platform": platform,
                "Error": error_message[:200],
            },
        )

    async def notify_performance_alert(
        self,
        client_name: str,
        campaign_name: str,
        metric: str,
        current_value: float,
        threshold: float,
        is_above: bool,
    ) -> bool:
        """Send performance alert notification.

        Args:
            client_name: Client name.
            campaign_name: Campaign name.
            metric: Metric that triggered alert.
            current_value: Current metric value.
            threshold: Threshold value.
            is_above: True if above threshold, False if below.

        Returns:
            True if notification sent.
        """
        direction = "above" if is_above else "below"
        message = f"Performance alert: {campaign_name} {metric} is {direction} threshold"

        return await self.send_slack(
            message=message,
            notification_type=NotificationType.PERFORMANCE_ALERT,
            details={
                "Client": client_name,
                "Campaign": campaign_name,
                "Metric": metric,
                "Current Value": f"{current_value:.2f}",
                "Threshold": f"{threshold:.2f}",
            },
        )

    async def notify_budget_alert(
        self,
        client_name: str,
        campaign_name: str,
        budget: float,
        spent: float,
        percent_used: float,
    ) -> bool:
        """Send budget alert notification.

        Args:
            client_name: Client name.
            campaign_name: Campaign name.
            budget: Total budget.
            spent: Amount spent.
            percent_used: Percentage of budget used.

        Returns:
            True if notification sent.
        """
        message = f"Budget alert: {campaign_name} has used {percent_used:.1f}% of budget"

        return await self.send_slack(
            message=message,
            notification_type=NotificationType.BUDGET_ALERT,
            details={
                "Client": client_name,
                "Campaign": campaign_name,
                "Budget": f"${budget:,.2f}",
                "Spent": f"${spent:,.2f}",
                "Remaining": f"${budget - spent:,.2f}",
            },
        )
