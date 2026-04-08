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

export default function Dashboard() {
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setIsLoading(true);
      setError("");

      try {
        const [conformance, volume, alertsPage] = await Promise.all([
          apiRequest("/analytics/conformance"),
          apiRequest("/analytics/volume"),
          apiRequest(`/alerts${toQueryString({ page: 1, page_size: 5 })}`)
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
          <SectionCard title="Compliance Trend" subtitle="30-day DMARC compliance">
            <Box
              sx={{
                height: 240,
                borderRadius: 3,
                border: "1px dashed #b8cff0",
                background:
                  "linear-gradient(180deg, rgba(246,250,255,0.8) 0%, rgba(255,255,255,0.9) 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                Chart placeholder for compliance trend
              </Typography>
            </Box>
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

