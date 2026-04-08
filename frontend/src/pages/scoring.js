import { useEffect, useState } from "react";
import { Alert, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";
import DataTable from "components/DataTable";
import { apiRequest } from "lib/apiClient";

export default function Scoring() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadScoring = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await apiRequest("/analytics/risk-trend");
        if (!isMounted) {
          return;
        }

        setRows(
          (response?.points || []).map((point) => ({
            id: point.at,
            source: new Date(point.at).toLocaleString(),
            score: String(point.score),
            status: String(point.risk_state || "unknown")
          }))
        );
      } catch (requestError) {
        if (!isMounted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Failed to load scoring data");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadScoring();
    return () => {
      isMounted = false;
    };
  }, []);

  const columns = [
    { key: "source", label: "Captured At" },
    { key: "score", label: "Risk Score" },
    { key: "status", label: "Risk State" }
  ];

  return (
    <AppLayout title="Scoring">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard title="Risk Scoring" subtitle="Enrichment + history">
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading risk trend...
              </Typography>
            ) : (
              <DataTable columns={columns} rows={rows} />
            )}
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
        {error ? (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        ) : null}
      </Grid>
    </AppLayout>
  );
}

