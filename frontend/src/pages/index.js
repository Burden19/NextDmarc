import { useEffect, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import StatCard from "components/StatCard";
import { apiRequest } from "lib/apiClient";

const DEFAULT_STATS = [
  { label: "DMARC Compliance", value: "--", helper: "Awaiting data" },
  { label: "Risk State", value: "--", helper: "Awaiting data" },
  { label: "Total Messages", value: "--", helper: "Awaiting data" },
  { label: "Domains Observed", value: "--", helper: "Awaiting data" }
];

function asPercentage(value) {
  if (typeof value !== "number") {
    return "0%";
  }
  return `${Math.round(value * 100)}%`;
}

export default function Overview() {
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadOverview = async () => {
      setError("");
      try {
        const [conformance, riskTrend, volume] = await Promise.all([
          apiRequest("/analytics/conformance"),
          apiRequest("/analytics/risk-trend"),
          apiRequest("/analytics/volume")
        ]);

        if (!isMounted) {
          return;
        }

        const points = riskTrend?.points || [];
        const latestPoint = points.length ? points[points.length - 1] : null;

        setStats([
          {
            label: "DMARC Compliance",
            value: asPercentage(conformance?.conformance_rate),
            helper: `${conformance?.total_messages || 0} total messages`
          },
          {
            label: "Risk State",
            value: latestPoint ? String(latestPoint.risk_state).toUpperCase() : "N/A",
            helper: latestPoint ? `Score ${latestPoint.score}` : "No scoring history yet"
          },
          {
            label: "Total Messages",
            value: `${volume?.total_messages || 0}`,
            helper: "Across all monitored domains"
          },
          {
            label: "Domains Observed",
            value: `${volume?.by_domain?.length || 0}`,
            helper: "From aggregate report volume"
          }
        ]);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Failed to load overview data");
      }
    };

    loadOverview();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppLayout title="Overview">
      <Grid container spacing={3}>
        {stats.map((item) => (
          <Grid item xs={12} md={3} key={item.label}>
            <StatCard {...item} />
          </Grid>
        ))}
        <Grid item xs={12} md={7}>
          <SectionCard
            title="Operational Snapshot"
            subtitle="DMARC posture across monitored domains"
            action={
              <Button variant="contained" component={Link} href="/dashboard">
                View Dashboard
              </Button>
            }
          >
            <Typography variant="body2" color="text.secondary">
              NextDmarc consolidates RUA collection, parsing, analysis, and alerting
              into a single SOC-friendly experience. Use the dashboard to track
              compliance, spoofing volume, and remediation progress.
            </Typography>
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="User Roles" subtitle="Four-actor governance model">
            <Box className="space-y-2">
              <Typography variant="body2">
                NEXTSTEP Admin: full platform control, tenant management, and security.
              </Typography>
              <Typography variant="body2">
                Client Admin: domain onboarding, policy control, and integrations.
              </Typography>
              <Typography variant="body2">
                Analyst SOC: monitoring, alert triage, and threat response.
              </Typography>
              <Typography variant="body2">
                Client User: reporting, dashboards, and compliance visibility.
              </Typography>
            </Box>
          </SectionCard>
        </Grid>
        {error ? (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        ) : null}
      </Grid>
    </AppLayout>
  );
}

