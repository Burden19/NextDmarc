import { Grid } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { domains } from "data/mock";

export default function Domains() {
  const columns = [
    { key: "name", label: "Domain" },
    { key: "policy", label: "Policy" },
    { key: "compliance", label: "Compliance" },
    { key: "risk", label: "Risk" }
  ];

  return (
    <AppLayout title="Domains">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard title="Monitored Domains" subtitle="Multi-tenant portfolio">
            <DataTable columns={columns} rows={domains} />
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

