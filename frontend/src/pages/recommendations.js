import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Button, Grid, Stack, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest } from "lib/apiClient";

export default function Recommendations() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRecommendations = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await apiRequest("/recommendations");
      setRows(
        (response || []).map((item) => {
          const entries = item.items || [];
          const firstEntry = entries[0];
          const title = firstEntry
            ? firstEntry.title
            : `Recommendation set for ${item.report_db_id}`;
          const extraCount = Math.max(0, entries.length - 1);

          return {
            id: item.report_db_id,
            reportDbId: item.report_db_id,
            resolved: !!item.resolved,
            title: extraCount ? `${title} (+${extraCount} more)` : title,
            impact: `Maturity ${item.maturity_level} (${item.maturity_score})`,
            status: item.resolved ? "Resolved" : "Open"
          };
        })
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to load recommendations"
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRecommendations();
  }, [loadRecommendations]);

  const handleResolveToggle = useCallback(
    async (row) => {
      const nextResolved = !row.resolved;
      let comment = "";

      if (nextResolved) {
        comment = window.prompt("Resolution comment", "Resolved from UI") || "";
      }

      setIsActing(true);
      setError("");
      setNotice("");
      try {
        await apiRequest(`/recommendations/${row.reportDbId}/resolve`, {
          method: "POST",
          body: {
            resolved: nextResolved,
            comment
          }
        });
        setNotice(nextResolved ? "Recommendation resolved" : "Recommendation reopened");
        await loadRecommendations();
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Failed to update recommendation status"
        );
      } finally {
        setIsActing(false);
      }
    },
    [loadRecommendations]
  );

  const columns = useMemo(
    () => [
      { key: "title", label: "Recommendation" },
      { key: "impact", label: "Expected Impact" },
      { key: "status", label: "Status" },
      {
        key: "actions",
        label: "Actions",
        render: (row) => (
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant={row.resolved ? "outlined" : "contained"}
              disabled={isActing}
              onClick={() => handleResolveToggle(row)}
            >
              {row.resolved ? "Reopen" : "Resolve"}
            </Button>
          </Stack>
        )
      }
    ],
    [handleResolveToggle, isActing]
  );

  return (
    <AppLayout title="Recommendations">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard title="DMARC Maturity" subtitle="Improvement roadmap">
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading recommendations...
              </Typography>
            ) : (
              <DataTable columns={columns} rows={rows} />
            )}
          </SectionCard>
        </Grid>
        {notice ? (
          <Grid item xs={12}>
            <Alert severity="success">{notice}</Alert>
          </Grid>
        ) : null}
        {error ? (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        ) : null}
      </Grid>
    </AppLayout>
  );
}
