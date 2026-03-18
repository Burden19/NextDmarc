import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";

export default function Settings() {
  return (
    <AppLayout title="Settings">
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <SectionCard title="Ingestion" subtitle="IMAP and mailbox configs">
            <Typography variant="body2" color="text.secondary">
              Configure collector mailboxes, RUA aliases, and encryption
              policies. Define retention for raw reports.
            </Typography>
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <SectionCard title="Notification Rules" subtitle="Alerting thresholds">
            <Typography variant="body2" color="text.secondary">
              Define escalation rules for high-risk spoofing, anomaly volume,
              and DMARC policy changes.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

