import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { reportPipeline } from "data/mock";

export default function Reports() {
  const columns = [
    { key: "stage", label: "Stage" },
    { key: "detail", label: "Detail" },
    { key: "status", label: "Status" }
  ];

  return (
    <AppLayout title="Reports">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard title="RUA Processing Pipeline" subtitle="Collection to analysis">
            <DataTable columns={columns} rows={reportPipeline} />
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="Parsing Notes" subtitle="Normalization rules">
            <Typography variant="body2" color="text.secondary">
              XML reports are normalized across providers (Google, Microsoft,
              Yahoo). Compression handling (ZIP, GZIP) and error quarantine are
              tracked here for auditability.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

