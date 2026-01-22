"""Report generation service with PDF, Excel, and CSV support."""

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.api.models import ReportFormat, ReportSection, ReportType
from src.graph.client import Neo4jClient, get_neo4j_client
from src.graph.queries import CypherQueries

logger = logging.getLogger(__name__)

# Reports directory
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


class ReportService:
    """Service for generating marketing performance reports."""

    def __init__(self, neo4j_client: Neo4jClient | None = None):
        """Initialize report service.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self._neo4j = neo4j_client or get_neo4j_client()
        self._queries = CypherQueries()

    async def generate(
        self,
        report_id: str,
        client_id: str,
        report_type: ReportType,
        format: ReportFormat,
        start_date: str,
        end_date: str,
        sections: list[ReportSection],
        include_recommendations: bool = True,
        compare_to_previous: bool = True,
        campaign_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a report.

        Args:
            report_id: Unique report identifier.
            client_id: Client ID.
            report_type: Type of report.
            format: Output format.
            start_date: Start date.
            end_date: End date.
            sections: Sections to include.
            include_recommendations: Include AI recommendations.
            compare_to_previous: Include comparison to previous period.
            campaign_ids: Specific campaigns to include.

        Returns:
            Generation result with file path and size.
        """
        logger.info(f"Generating {format.value} report for client {client_id}")

        # Gather data
        data = self._gather_report_data(
            client_id,
            start_date,
            end_date,
            sections,
            compare_to_previous,
            campaign_ids,
        )

        # Generate recommendations if requested
        if include_recommendations and ReportSection.RECOMMENDATIONS in sections:
            data["recommendations"] = self._generate_recommendations(data)

        # Generate report in requested format
        if format == ReportFormat.PDF:
            file_path = await self._generate_pdf(report_id, data, client_id)
        elif format == ReportFormat.EXCEL:
            file_path = await self._generate_excel(report_id, data, client_id)
        elif format == ReportFormat.CSV:
            file_path = await self._generate_csv(report_id, data, client_id)
        elif format in [ReportFormat.GOOGLE_DOCS, ReportFormat.GOOGLE_SHEETS]:
            # For MVP, generate locally; Google integration would go here
            file_path = await self._generate_excel(report_id, data, client_id)
        else:
            raise ValueError(f"Unsupported format: {format}")

        file_size = file_path.stat().st_size if file_path.exists() else 0

        return {
            "file_path": str(file_path),
            "file_size": file_size,
        }

    def _gather_report_data(
        self,
        client_id: str,
        start_date: str,
        end_date: str,
        sections: list[ReportSection],
        compare_to_previous: bool,
        campaign_ids: list[str] | None,
    ) -> dict[str, Any]:
        """Gather all data needed for the report.

        Args:
            client_id: Client ID.
            start_date: Start date.
            end_date: End date.
            sections: Sections to include.
            compare_to_previous: Include comparison.
            campaign_ids: Specific campaigns.

        Returns:
            Dictionary with all report data.
        """
        data: dict[str, Any] = {
            "client_id": client_id,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Get client info
        client_result = self._neo4j.execute_query(
            "MATCH (c:Client {id: $client_id}) RETURN c",
            {"client_id": client_id},
        )
        if client_result:
            data["client"] = client_result[0]["c"]

        # Summary section
        if ReportSection.SUMMARY in sections:
            data["summary"] = self._get_summary(client_id, start_date, end_date)

        # Campaigns section
        if ReportSection.CAMPAIGNS in sections:
            data["campaigns"] = self._get_campaign_data(
                client_id, start_date, end_date, campaign_ids
            )

        # Ad Sets section
        if ReportSection.AD_SETS in sections:
            data["ad_sets"] = self._get_adset_data(client_id, start_date, end_date)

        # Trends section
        if ReportSection.TRENDS in sections:
            data["trends"] = self._get_trend_data(client_id, start_date, end_date)

        # Channel breakdown
        if ReportSection.CHANNEL_BREAKDOWN in sections:
            data["channels"] = self._get_channel_breakdown(
                client_id, start_date, end_date
            )

        # Comparison to previous period
        if compare_to_previous:
            # Calculate previous period
            from datetime import timedelta

            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            period_days = (end - start).days

            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days)

            data["previous_period"] = self._get_summary(
                client_id,
                prev_start.strftime("%Y-%m-%d"),
                prev_end.strftime("%Y-%m-%d"),
            )

        return data

    def _get_summary(
        self, client_id: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Get summary metrics."""
        result = self._neo4j.execute_query(
            self._queries.GET_CLIENT_SUMMARY,
            {"client_id": client_id, "start_date": start_date, "end_date": end_date},
        )

        if result:
            return result[0]
        return {}

    def _get_campaign_data(
        self,
        client_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Get campaign performance data."""
        statuses = ["active", "paused", "completed"]

        result = self._neo4j.execute_query(
            self._queries.GET_CAMPAIGN_COMPARISON,
            {
                "client_id": client_id,
                "start_date": start_date,
                "end_date": end_date,
                "statuses": statuses,
            },
        )

        campaigns = result or []

        # Filter to specific campaigns if requested
        if campaign_ids:
            campaigns = [c for c in campaigns if c.get("campaign_id") in campaign_ids]

        return campaigns

    def _get_adset_data(
        self, client_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Get ad set performance data."""
        query = """
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:CONTAINS]->(adset:AdSet)
        OPTIONAL MATCH (m:Metric {entity_type: 'adset', entity_id: adset.id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        WITH adset, camp, m
        RETURN adset.id AS adset_id,
               adset.name AS adset_name,
               camp.name AS campaign_name,
               sum(m.impressions) AS impressions,
               sum(m.clicks) AS clicks,
               sum(m.conversions) AS conversions,
               sum(m.spend) AS spend
        ORDER BY spend DESC
        LIMIT 50
        """
        return self._neo4j.execute_query(
            query,
            {"client_id": client_id, "start_date": start_date, "end_date": end_date},
        )

    def _get_trend_data(
        self, client_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Get daily trend data."""
        return self._neo4j.execute_query(
            self._queries.GET_DAILY_METRICS,
            {"client_id": client_id, "start_date": start_date, "end_date": end_date},
        )

    def _get_channel_breakdown(
        self, client_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Get channel breakdown data."""
        return self._neo4j.execute_query(
            self._queries.GET_CHANNEL_BREAKDOWN,
            {"client_id": client_id, "start_date": start_date, "end_date": end_date},
        )

    def _generate_recommendations(self, data: dict[str, Any]) -> list[str]:
        """Generate AI recommendations based on data."""
        recommendations = []

        summary = data.get("summary", {})
        campaigns = data.get("campaigns", [])

        # Check for low CTR
        avg_ctr = summary.get("avg_ctr", 0)
        if avg_ctr and avg_ctr < 1.0:
            recommendations.append(
                f"Overall CTR is {avg_ctr:.2f}%, below the 1% benchmark. "
                "Consider reviewing ad creative and targeting."
            )

        # Check ROAS
        roas = summary.get("roas")
        if roas and roas < 2.0:
            recommendations.append(
                f"Current ROAS is {roas:.2f}x. Consider optimizing "
                "campaigns with low return on ad spend."
            )

        # Identify top performers
        if campaigns:
            top_campaign = max(
                campaigns,
                key=lambda c: c.get("roas") or 0,
                default=None,
            )
            if top_campaign and top_campaign.get("roas"):
                recommendations.append(
                    f"'{top_campaign.get('campaign_name')}' has the highest ROAS "
                    f"({top_campaign.get('roas'):.2f}x). Consider increasing its budget allocation."
                )

            # Identify underperformers
            underperformers = [
                c for c in campaigns if c.get("spend", 0) > 100 and (c.get("roas") or 0) < 1.0
            ]
            if underperformers:
                names = ", ".join(c.get("campaign_name", "Unknown")[:20] for c in underperformers[:3])
                recommendations.append(
                    f"Campaigns with low ROAS: {names}. Review targeting and creative."
                )

        return recommendations[:5]

    async def _generate_pdf(
        self, report_id: str, data: dict[str, Any], client_id: str
    ) -> Path:
        """Generate PDF report."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        file_path = REPORTS_DIR / f"{report_id}.pdf"
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontSize=24,
            spaceAfter=20,
        )
        elements.append(
            Paragraph(
                f"Marketing Performance Report",
                title_style,
            )
        )

        # Subtitle with client and date range
        client_name = data.get("client", {}).get("name", client_id)
        elements.append(
            Paragraph(
                f"{client_name} | {data['start_date']} to {data['end_date']}",
                styles["Heading2"],
            )
        )
        elements.append(Spacer(1, 0.3 * inch))

        # Summary section
        if "summary" in data:
            elements.append(Paragraph("Executive Summary", styles["Heading2"]))
            summary = data["summary"]

            summary_data = [
                ["Metric", "Value"],
                ["Total Impressions", f"{summary.get('total_impressions', 0):,}"],
                ["Total Clicks", f"{summary.get('total_clicks', 0):,}"],
                ["Total Conversions", f"{summary.get('total_conversions', 0):,}"],
                ["Total Spend", f"${summary.get('total_spend', 0):,.2f}"],
                ["Average CTR", f"{summary.get('avg_ctr', 0):.2f}%"],
            ]
            if summary.get("roas"):
                summary_data.append(["ROAS", f"{summary.get('roas'):.2f}x"])

            table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

        # Campaign performance table
        if "campaigns" in data and data["campaigns"]:
            elements.append(Paragraph("Campaign Performance", styles["Heading2"]))

            campaign_data = [
                ["Campaign", "Spend", "Clicks", "Conv.", "ROAS"]
            ]
            for camp in data["campaigns"][:10]:
                campaign_data.append(
                    [
                        camp.get("campaign_name", "")[:30],
                        f"${camp.get('spend', 0):,.0f}",
                        f"{camp.get('clicks', 0):,}",
                        f"{camp.get('conversions', 0):,}",
                        f"{camp.get('roas', 0):.2f}x" if camp.get("roas") else "N/A",
                    ]
                )

            table = Table(campaign_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 0.8 * inch, 0.8 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

        # Recommendations
        if "recommendations" in data and data["recommendations"]:
            elements.append(Paragraph("Recommendations", styles["Heading2"]))
            for rec in data["recommendations"]:
                elements.append(Paragraph(f"• {rec}", styles["Normal"]))
                elements.append(Spacer(1, 0.1 * inch))

        # Footer
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(
            Paragraph(
                f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            )
        )

        doc.build(elements)
        logger.info(f"PDF report generated: {file_path}")
        return file_path

    async def _generate_excel(
        self, report_id: str, data: dict[str, Any], client_id: str
    ) -> Path:
        """Generate Excel report."""
        import pandas as pd

        file_path = REPORTS_DIR / f"{report_id}.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            # Summary sheet
            if "summary" in data:
                summary_df = pd.DataFrame([data["summary"]])
                summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Campaigns sheet
            if "campaigns" in data and data["campaigns"]:
                campaigns_df = pd.DataFrame(data["campaigns"])
                campaigns_df.to_excel(writer, sheet_name="Campaigns", index=False)

            # Ad Sets sheet
            if "ad_sets" in data and data["ad_sets"]:
                adsets_df = pd.DataFrame(data["ad_sets"])
                adsets_df.to_excel(writer, sheet_name="Ad Sets", index=False)

            # Daily Trends sheet
            if "trends" in data and data["trends"]:
                trends_df = pd.DataFrame(data["trends"])
                trends_df.to_excel(writer, sheet_name="Daily Trends", index=False)

            # Channels sheet
            if "channels" in data and data["channels"]:
                channels_df = pd.DataFrame(data["channels"])
                channels_df.to_excel(writer, sheet_name="Channels", index=False)

            # Recommendations sheet
            if "recommendations" in data and data["recommendations"]:
                rec_df = pd.DataFrame({"Recommendations": data["recommendations"]})
                rec_df.to_excel(writer, sheet_name="Recommendations", index=False)

        logger.info(f"Excel report generated: {file_path}")
        return file_path

    async def _generate_csv(
        self, report_id: str, data: dict[str, Any], client_id: str
    ) -> Path:
        """Generate CSV report (campaigns only)."""
        import pandas as pd

        file_path = REPORTS_DIR / f"{report_id}.csv"

        if "campaigns" in data and data["campaigns"]:
            campaigns_df = pd.DataFrame(data["campaigns"])
            campaigns_df.to_csv(file_path, index=False)
        else:
            # Empty file if no campaigns
            file_path.write_text("")

        logger.info(f"CSV report generated: {file_path}")
        return file_path

    def get_report_path(self, report_id: str) -> Path | None:
        """Get the file path for a report.

        Args:
            report_id: Report ID.

        Returns:
            Path to report file or None.
        """
        for ext in [".pdf", ".xlsx", ".csv"]:
            path = REPORTS_DIR / f"{report_id}{ext}"
            if path.exists():
                return path
        return None
