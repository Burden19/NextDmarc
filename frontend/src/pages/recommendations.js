import { Grid } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { recommendations } from "data/mock";

export default function Recommendations() {
  const columns = [
    { key: "title", label: "Recommendation" },
    { key: "impact", label: "Expected Impact" },
    { key: "status", label: "Status" }
  ];

  return (
    <AppLayout title="Recommendations">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard title="DMARC Maturity" subtitle="Improvement roadmap">
            <DataTable columns={columns} rows={recommendations} />
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

