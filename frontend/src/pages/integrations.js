import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest } from "lib/apiClient";

export default function Integrations() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    name: "",
    kind: "slack",
    configText: '{"webhook_url":"https://hooks.slack.com/services/example"}',
    enabled: true
  });

  const loadIntegrations = async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await apiRequest("/integrations");
      setRows(
        (response || []).map((item) => ({
          id: item.id,
          name: item.name,
          kind: item.kind,
          enabled: !!item.enabled,
          status: item.enabled ? "Enabled" : "Disabled",
          owner: String(item.kind || "unknown").toUpperCase(),
          config: item.config || {}
        }))
      );
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load integrations");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleFormChange = (field) => (event) => {
    const value = field === "enabled" ? event.target.checked : event.target.value;
    setForm((previous) => ({ ...previous, [field]: value }));
  };

  const parseConfig = () => {
    try {
      const parsed = JSON.parse(form.configText || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Config must be a JSON object");
      }
      return parsed;
    } catch {
      throw new Error("Integration config must be valid JSON object");
    }
  };

  const handleCreate = async () => {
    setIsActing(true);
    setError("");
    setNotice("");
    try {
      const config = parseConfig();
      await apiRequest("/integrations", {
        method: "POST",
        body: {
          name: form.name.trim(),
          kind: form.kind,
          config,
          enabled: form.enabled
        }
      });

      setForm((previous) => ({
        ...previous,
        name: ""
      }));
      setNotice("Integration created");
      await loadIntegrations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to create integration");
    } finally {
      setIsActing(false);
    }
  };

  const handleTest = async (row) => {
    setIsActing(true);
    setError("");
    setNotice("");
    try {
      const response = await apiRequest(`/integrations/${row.id}/test`, {
        method: "POST"
      });
      const outcome = String(response?.status || "unknown").toUpperCase();
      setNotice(`Connector test result: ${outcome}`);
      await loadIntegrations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to test integration");
    } finally {
      setIsActing(false);
    }
  };

  const handleToggleEnabled = async (row) => {
    setIsActing(true);
    setError("");
    setNotice("");
    try {
      await apiRequest(`/integrations/${row.id}`, {
        method: "PATCH",
        body: {
          enabled: !row.enabled
        }
      });
      setNotice(row.enabled ? "Integration disabled" : "Integration enabled");
      await loadIntegrations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to update integration");
    } finally {
      setIsActing(false);
    }
  };

  const handleDelete = async (row) => {
    const confirmed = window.confirm(`Delete integration ${row.name}?`);
    if (!confirmed) {
      return;
    }

    setIsActing(true);
    setError("");
    setNotice("");
    try {
      await apiRequest(`/integrations/${row.id}`, {
        method: "DELETE"
      });
      setNotice("Integration deleted");
      await loadIntegrations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to delete integration");
    } finally {
      setIsActing(false);
    }
  };

  const columns = [
    { key: "name", label: "Connector" },
    { key: "status", label: "Status" },
    { key: "owner", label: "Type" },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <Stack direction="row" spacing={1}>
          <Button size="small" variant="outlined" disabled={isActing} onClick={() => handleTest(row)}>
            Test
          </Button>
          <Button size="small" variant="outlined" disabled={isActing} onClick={() => handleToggleEnabled(row)}>
            {row.enabled ? "Disable" : "Enable"}
          </Button>
          <Button size="small" color="error" variant="outlined" disabled={isActing} onClick={() => handleDelete(row)}>
            Delete
          </Button>
        </Stack>
      )
    }
  ];

  return (
    <AppLayout title="Integrations">
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <SectionCard title="SOC Integrations" subtitle="SIEM, SOAR, ChatOps">
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading integrations...
              </Typography>
            ) : (
              <DataTable columns={columns} rows={rows} />
            )}
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <SectionCard title="Create Integration">
            <Stack spacing={1.2}>
              <TextField
                size="small"
                label="Connector Name"
                value={form.name}
                onChange={handleFormChange("name")}
              />
              <TextField
                select
                size="small"
                label="Kind"
                value={form.kind}
                onChange={handleFormChange("kind")}
              >
                <MenuItem value="email">email</MenuItem>
                <MenuItem value="slack">slack</MenuItem>
                <MenuItem value="siem">siem</MenuItem>
              </TextField>
              <TextField
                size="small"
                multiline
                minRows={4}
                label="Config JSON"
                value={form.configText}
                onChange={handleFormChange("configText")}
              />
              <FormControlLabel
                control={<Checkbox checked={form.enabled} onChange={handleFormChange("enabled")} />}
                label="Enabled"
              />
              <Box>
                <Button variant="contained" onClick={handleCreate} disabled={isActing || !form.name.trim()}>
                  Create
                </Button>
              </Box>
              <Typography variant="caption" color="text.secondary">
                Tip: email config needs sender and recipients; slack needs webhook_url; siem needs endpoint.
              </Typography>
            </Stack>
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

