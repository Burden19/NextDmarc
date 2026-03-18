import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import DataTable from "components/DataTable";

const scoringRows = [
  {
    id: "score-1",
    source: "198.51.100.24",
    score: "82",
    classification: "Malicious"
  },
  {
    id: "score-2",
    source: "203.0.113.88",
    score: "54",
    classification: "Suspicious"
  },
  {
    id: "score-3",
    source: "192.0.2.9",
    score: "21",
    classification: "Legitimate"
  }
];

export default function Scoring() {
  const columns = [
    { key: "source", label: "Source" },
    { key: "score", label: "Risk Score" },
    { key: "classification", label: "Classification" }
  ];

  return (
    <AppLayout title="Scoring">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard title="Risk Scoring" subtitle="Enrichment + history">
            <DataTable columns={columns} rows={scoringRows} />
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="Threat Intelligence">
            <Typography variant="body2" color="text.secondary">
              Scores combine DMARC failures, geo/ASN context, and historical
              anomalies. Analysts can pivot into IOC exports and SIEM.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

