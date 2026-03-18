import Link from "next/link";
import { Box, Button, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import StatCard from "components/StatCard";
import { stats } from "data/mock";

export default function Overview() {
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
      </Grid>
    </AppLayout>
  );
}

