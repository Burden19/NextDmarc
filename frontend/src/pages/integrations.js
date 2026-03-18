import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { integrationItems } from "data/mock";

export default function Integrations() {
  const columns = [
    { key: "name", label: "Connector" },
    { key: "status", label: "Status" },
    { key: "owner", label: "Owner" }
  ];

  return (
    <AppLayout title="Integrations">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard title="SOC Integrations" subtitle="SIEM, SOAR, ChatOps">
            <DataTable columns={columns} rows={integrationItems} />
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="API & Webhooks">
            <Typography variant="body2" color="text.secondary">
              APIs expose DMARC analytics, alerts, and IOC exports. Webhooks
              support real-time notifications for SOAR and ticketing systems.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

