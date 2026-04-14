import { useEffect, useState } from "react";
import { Alert, Box, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import StatCard from "components/StatCard";
import AlertList from "components/AlertList";
import { apiRequest, toQueryString } from "lib/apiClient";

const DEFAULT_STATS = [
  { label: "DMARC Compliance", value: "--", helper: "Awaiting data" },
  { label: "Total Messages", value: "--", helper: "Awaiting data" },
  { label: "SPF Pass Rate", value: "--", helper: "Awaiting data" },
  { label: "DKIM Pass Rate", value: "--", helper: "Awaiting data" }
];

const TREND_CHART_WIDTH = 760;
const TREND_CHART_HEIGHT = 220;
const TREND_PADDING_X = 24;
const TREND_PADDING_Y = 20;

function asPercentage(value) {
  if (typeof value !== "number") {
    return "0%";
  }
  return `${Math.round(value * 100)}%`;
}

function mapAlertColor(severity) {
  const normalized = String(severity || "").toLowerCase();
  if (normalized === "high" || normalized === "critical") {
    return "error";
  }
  if (normalized === "medium") {
    return "warning";
  }
  if (normalized === "low") {
    return "success";
  }
  return "info";
}

function asNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function asTimestamp(value) {
  const parsed = Date.parse(String(value || ""));
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatShortDate(value) {
  if (!value) {
    return "N/A";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleDateString();
}

function RiskTrendChart({ points, isLoading }) {
  if (isLoading) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading risk trend...
      </Typography>
    );
  }

  if (!points.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No scoring history yet. The trend will appear after scoring snapshots are stored.
      </Typography>
    );
  }

  const values = points.map((point) => asNumber(point.score));
  const minScore = Math.min(...values);
  const maxScore = Math.max(...values);
  const scoreRange = Math.max(1, maxScore - minScore);
  const graphWidth = TREND_CHART_WIDTH - TREND_PADDING_X * 2;
  const graphHeight = TREND_CHART_HEIGHT - TREND_PADDING_Y * 2;
  const denominator = Math.max(1, points.length - 1);

  const xAt = (index) => TREND_PADDING_X + (index * graphWidth) / denominator;
  const yAt = (score) =>
    TREND_CHART_HEIGHT - TREND_PADDING_Y - ((score - minScore) * graphHeight) / scoreRange;

  const linePath = points
    .map((point, index) => {
      const x = xAt(index).toFixed(2);
      const y = yAt(asNumber(point.score)).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  const firstPoint = points[0];
  const latestPoint = points[points.length - 1];
  const areaPath = `${linePath} L ${xAt(points.length - 1).toFixed(2)} ${(TREND_CHART_HEIGHT - TREND_PADDING_Y).toFixed(2)} L ${xAt(0).toFixed(2)} ${(TREND_CHART_HEIGHT - TREND_PADDING_Y).toFixed(2)} Z`;

  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Last {points.length} snapshots • Latest score {latestPoint.score} (
        {String(latestPoint.risk_state || "unknown").toUpperCase()})
      </Typography>
      <Box
        component="svg"
        viewBox={`0 0 ${TREND_CHART_WIDTH} ${TREND_CHART_HEIGHT}`}
        role="img"
        aria-label="Risk trend chart"
        sx={{ width: "100%", height: 220, mt: 1, borderRadius: 2, backgroundColor: "#fbfdff" }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((step) => {
          const y = TREND_PADDING_Y + graphHeight * step;
          return (
            <line
              key={`grid-${step}`}
              x1={TREND_PADDING_X}
              y1={y}
              x2={TREND_CHART_WIDTH - TREND_PADDING_X}
              y2={y}
              stroke="#dde7f5"
              strokeDasharray="4 4"
            />
          );
        })}
        <path d={areaPath} fill="rgba(15, 76, 151, 0.12)" />
        <path d={linePath} fill="none" stroke="#0f4c97" strokeWidth="3" strokeLinecap="round" />
        {points.map((point, index) => {
          const cx = xAt(index);
          const cy = yAt(asNumber(point.score));
          return (
            <circle key={`${point.at}-${index}`} cx={cx} cy={cy} r="3.8" fill="#0f4c97">
              <title>{`${formatShortDate(point.at)} • Score ${point.score} • ${String(point.risk_state || "unknown")}`}</title>
            </circle>
          );
        })}
      </Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          {formatShortDate(firstPoint.at)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatShortDate(latestPoint.at)}
        </Typography>
      </Box>
    </Box>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [alerts, setAlerts] = useState([]);
  const [trendPoints, setTrendPoints] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setIsLoading(true);
      setError("");

      try {
        const [conformance, volume, alertsPage, riskTrend] = await Promise.all([
          apiRequest("/analytics/conformance"),
          apiRequest("/analytics/volume"),
          apiRequest(`/alerts${toQueryString({ page: 1, page_size: 5 })}`),
          apiRequest("/analytics/risk-trend")
        ]);

        if (!isMounted) {
          return;
        }

        setStats([
          {
            label: "DMARC Compliance",
            value: asPercentage(conformance?.conformance_rate),
            helper: `${conformance?.total_messages || 0} total messages`
          },
          {
            label: "Total Messages",
            value: `${volume?.total_messages || 0}`,
            helper: `${volume?.by_domain?.length || 0} domains observed`
          },
          {
            label: "SPF Pass Rate",
            value: asPercentage(conformance?.spf_pass_rate),
            helper: "From aggregate records"
          },
          {
            label: "DKIM Pass Rate",
            value: asPercentage(conformance?.dkim_pass_rate),
            helper: "From aggregate records"
          }
        ]);

        setAlerts(
          (alertsPage?.items || []).map((item) => ({
            id: item.id,
            title: item.message,
            severity: String(item.severity || "unknown").toUpperCase(),
            detail: item.assignee
              ? `Status: ${item.status} • Assignee: ${item.assignee}`
              : `Status: ${item.status}`,
            color: mapAlertColor(item.severity)
          }))
        );

        const orderedTrendPoints = [...(riskTrend?.points || [])]
          .sort((left, right) => asTimestamp(left.at) - asTimestamp(right.at))
          .slice(-30);
        setTrendPoints(orderedTrendPoints);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Failed to load dashboard data");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppLayout title="Dashboard">
      <Grid container spacing={3}>
        {stats.map((item) => (
          <Grid item xs={12} md={3} key={item.label}>
            <StatCard {...item} />
          </Grid>
        ))}
        <Grid item xs={12} md={8}>
          <SectionCard title="Risk Trend" subtitle="Latest 30 scoring snapshots">
            <RiskTrendChart points={trendPoints} isLoading={isLoading} />
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <SectionCard title="Priority Alerts" subtitle="SOC triage queue">
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading alerts...
              </Typography>
            ) : alerts.length ? (
              <AlertList items={alerts} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No alerts available for this tenant yet.
              </Typography>
            )}
          </SectionCard>
        </Grid>
        {error ? (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        ) : null}
        <Grid item xs={12}>
          <SectionCard title="Operational Notes">
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 860 }}>
              Add analyst playbooks, response SLAs, and integration health status
              here to keep the SOC aligned.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

