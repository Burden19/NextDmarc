import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import AlertList from "components/AlertList";
import SectionCard from "components/SectionCard";
import { recentAlerts } from "data/mock";

export default function Alerts() {
  return (
    <AppLayout title="Alerts">
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <SectionCard title="Active Alerts" subtitle="Live DMARC anomalies">
            <AlertList items={recentAlerts} />
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <SectionCard title="Response Guidance">
            <Typography variant="body2" color="text.secondary">
              Analysts validate spoofing, escalate via SOAR, and update
              suppression or allow-lists. Critical events trigger real-time
              notifications and IOC exports.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

