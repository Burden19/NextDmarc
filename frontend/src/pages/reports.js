import { useEffect, useState } from "react";
import { Alert, Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest, toQueryString } from "lib/apiClient";

export default function Reports() {
  const [rows, setRows] = useState([]);
  const [totalReports, setTotalReports] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadReports = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await apiRequest(`/reports${toQueryString({ page: 1, page_size: 25 })}`);

        if (!isMounted) {
          return;
        }

        const items = response?.items || [];
        setRows(
          items.map((item) => ({
            id: item.id,
            report: item.report_id,
            reporter: item.reporter_org,
            window: `${new Date(item.date_range_begin).toLocaleDateString()} - ${new Date(item.date_range_end).toLocaleDateString()}`,
            created: new Date(item.created_at).toLocaleString()
          }))
        );
        setTotalReports(response?.total || 0);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Failed to load reports");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadReports();
    return () => {
      isMounted = false;
    };
  }, []);

  const columns = [
    { key: "report", label: "Report ID" },
    { key: "reporter", label: "Reporter" },
    { key: "window", label: "Date Range" },
    { key: "created", label: "Created" }
  ];

  return (
    <AppLayout title="Reports">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard
            title="RUA Reports"
            subtitle={isLoading ? "Loading..." : `${totalReports} reports available`}
          >
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading reports...
              </Typography>
            ) : (
              <DataTable columns={columns} rows={rows} />
            )}
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="Parsing Notes" subtitle="Normalization rules">
            <Typography variant="body2" color="text.secondary">
              Reports are fetched from tenant-scoped backend storage. Use this
              table to inspect reporting windows and producer organizations
              before drilling into records and source intelligence.
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

