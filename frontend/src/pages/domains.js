import { useEffect, useState } from "react";
import { Grid } from "@mui/material";
import { Alert, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest } from "lib/apiClient";

export default function Domains() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadDomains = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await apiRequest("/domains");
        if (!isMounted) {
          return;
        }

        setRows(
          (response || []).map((item) => ({
            id: item.id,
            name: item.fqdn,
            policy: item.dmarc_policy,
            status: item.status,
            updated: new Date(item.updated_at).toLocaleString()
          }))
        );
      } catch (requestError) {
        if (!isMounted) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Failed to load domains");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadDomains();
    return () => {
      isMounted = false;
    };
  }, []);

  const columns = [
    { key: "name", label: "Domain" },
    { key: "policy", label: "Policy" },
    { key: "status", label: "Status" },
    { key: "updated", label: "Updated" }
  ];

  return (
    <AppLayout title="Domains">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard title="Monitored Domains" subtitle="Multi-tenant portfolio">
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading domains...
              </Typography>
            ) : (
              <DataTable columns={columns} rows={rows} />
            )}
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

