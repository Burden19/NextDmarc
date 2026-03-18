import { Box, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import StatCard from "components/StatCard";
import { recentAlerts, stats } from "data/mock";
import AlertList from "components/AlertList";

export default function Dashboard() {
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
            <AlertList items={recentAlerts} />
          </SectionCard>
        </Grid>
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

