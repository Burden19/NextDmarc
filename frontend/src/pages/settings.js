import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { roleLabels } from "access/roles";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest, toQueryString } from "lib/apiClient";
import { getAuthSession } from "lib/authSession";

const EMPTY_MAILBOX_FORM = {
  name: "",
  server: "",
  username: "",
  password: "",
  mailbox: "INBOX",
  enabled: true
};

const SERVICE_PROBES = [
  {
    id: "svc-nextstep-domain-governance",
    role: "nextstep_admin",
    service: "Domain Governance",
    endpoint: "/domains",
    purpose: "Track tenant domains and DMARC policy posture.",
    href: "/domains"
  },
  {
    id: "svc-nextstep-integration-fleet",
    role: "nextstep_admin",
    service: "Integration Fleet",
    endpoint: "/integrations",
    purpose: "Audit ChatOps, SIEM, and outbound connectors.",
    href: "/integrations"
  },
  {
    id: "svc-client-mailbox-ingestion",
    role: "client_admin",
    service: "Mailbox Ingestion",
    endpoint: "/mailboxes",
    purpose: "Validate mailbox availability for DMARC collection.",
    href: "/settings"
  },
  {
    id: "svc-client-recommendations",
    role: "client_admin",
    service: "Policy Recommendations",
    endpoint: "/recommendations",
    purpose: "Track unresolved posture improvement tasks.",
    href: "/recommendations"
  },
  {
    id: "svc-analyst-alert-queue",
    role: "analyst_soc",
    service: "Alert Queue",
    endpoint: `/alerts${toQueryString({ page: 1, page_size: 25 })}`,
    purpose: "Inspect triage backlog and escalation pressure.",
    href: "/alerts"
  },
  {
    id: "svc-analyst-ioc-feed",
    role: "analyst_soc",
    service: "IOC Feed",
    endpoint: "/ioc/json",
    purpose: "Export active source indicators for SOC pivoting.",
    href: null
  },
  {
    id: "svc-client-user-conformance",
    role: "client_user",
    service: "Conformance Snapshot",
    endpoint: "/analytics/conformance",
    purpose: "Monitor tenant DMARC pass rates and coverage.",
    href: "/dashboard"
  },
  {
    id: "svc-client-user-report-feed",
    role: "client_user",
    service: "Report Feed",
    endpoint: `/reports${toQueryString({ page: 1, page_size: 25 })}`,
    purpose: "Follow inbound aggregate report cadence.",
    href: "/reports"
  }
];

function asDateTime(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function asPercent(value) {
  if (typeof value !== "number") {
    return "0%";
  }
  return `${Math.round(value * 100)}%`;
}

function buildServiceRows() {
  return SERVICE_PROBES.map((probe) => ({
    ...probe,
    roleLabel: roleLabels[probe.role] || probe.role,
    status: "idle",
    metric: "Not checked",
    checkedAt: "-",
    lastError: ""
  }));
}

function summarizeProbeMetric(probeId, payload) {
  switch (probeId) {
    case "svc-nextstep-domain-governance": {
      const total = Array.isArray(payload) ? payload.length : 0;
      return `${total} domains`;
    }
    case "svc-nextstep-integration-fleet": {
      const items = Array.isArray(payload) ? payload : [];
      const enabled = items.filter((item) => !!item.enabled).length;
      return `${enabled}/${items.length} enabled`;
    }
    case "svc-client-mailbox-ingestion": {
      const items = Array.isArray(payload) ? payload : [];
      const enabled = items.filter((item) => !!item.enabled).length;
      return `${enabled}/${items.length} mailboxes enabled`;
    }
    case "svc-client-recommendations": {
      const items = Array.isArray(payload) ? payload : [];
      const open = items.filter((item) => !item.resolved).length;
      return `${open} open of ${items.length}`;
    }
    case "svc-analyst-alert-queue": {
      const total =
        typeof payload?.total === "number"
          ? payload.total
          : Array.isArray(payload?.items)
            ? payload.items.length
            : 0;
      return `${total} queued alerts`;
    }
    case "svc-analyst-ioc-feed": {
      const total =
        typeof payload?.total === "number"
          ? payload.total
          : Array.isArray(payload?.items)
            ? payload.items.length
            : 0;
      return `${total} indicators`;
    }
    case "svc-client-user-conformance": {
      const rate = asPercent(payload?.conformance_rate);
      const totalMessages = typeof payload?.total_messages === "number" ? payload.total_messages : 0;
      return `${rate} across ${totalMessages} messages`;
    }
    case "svc-client-user-report-feed": {
      const total =
        typeof payload?.total === "number"
          ? payload.total
          : Array.isArray(payload?.items)
            ? payload.items.length
            : 0;
      return `${total} reports`;
    }
    default:
      return "Checked";
  }
}

function normalizeMailboxRow(item) {
  return {
    id: item.id,
    name: item.name,
    server: item.server,
    username: item.username,
    mailbox: item.mailbox,
    enabled: !!item.enabled,
    updatedAt: asDateTime(item.updated_at)
  };
}

export default function Settings() {
  const [mailboxes, setMailboxes] = useState([]);
  const [isLoadingMailboxes, setIsLoadingMailboxes] = useState(true);
  const [isMailboxActionRunning, setIsMailboxActionRunning] = useState(false);
  const [mailboxForm, setMailboxForm] = useState(EMPTY_MAILBOX_FORM);
  const [mailboxNotice, setMailboxNotice] = useState("");
  const [mailboxError, setMailboxError] = useState("");

  const [serviceRows, setServiceRows] = useState(buildServiceRows);
  const [serviceRoleFilter, setServiceRoleFilter] = useState("all");
  const [isRunningAllProbes, setIsRunningAllProbes] = useState(false);
  const [probeBusyById, setProbeBusyById] = useState({});

  const currentRole = useMemo(() => getAuthSession()?.role || "unknown", []);

  const loadMailboxes = useCallback(async () => {
    setIsLoadingMailboxes(true);
    setMailboxError("");
    try {
      const response = await apiRequest("/mailboxes");
      const items = Array.isArray(response) ? response : [];
      setMailboxes(items.map((item) => normalizeMailboxRow(item)));
    } catch (requestError) {
      setMailboxError(
        requestError instanceof Error ? requestError.message : "Failed to load mailboxes"
      );
    } finally {
      setIsLoadingMailboxes(false);
    }
  }, []);

  useEffect(() => {
    loadMailboxes();
  }, [loadMailboxes]);

  const handleMailboxFormChange = (field) => (event) => {
    const value = field === "enabled" ? event.target.checked : event.target.value;
    setMailboxForm((previous) => ({
      ...previous,
      [field]: value
    }));
  };

  const handleCreateMailbox = async () => {
    setIsMailboxActionRunning(true);
    setMailboxNotice("");
    setMailboxError("");

    try {
      const created = await apiRequest("/mailboxes", {
        method: "POST",
        body: {
          name: mailboxForm.name.trim(),
          username: mailboxForm.username.trim(),
          password: mailboxForm.password,
          server: mailboxForm.server.trim(),
          mailbox: mailboxForm.mailbox.trim() || "INBOX"
        }
      });

      if (!mailboxForm.enabled && created?.id) {
        await apiRequest(`/mailboxes/${created.id}`, {
          method: "PATCH",
          body: {
            enabled: false
          }
        });
      }

      setMailboxForm(EMPTY_MAILBOX_FORM);
      setMailboxNotice("Mailbox created successfully");
      await loadMailboxes();
    } catch (requestError) {
      setMailboxError(requestError instanceof Error ? requestError.message : "Failed to create mailbox");
    } finally {
      setIsMailboxActionRunning(false);
    }
  };

  const runMailboxAction = useCallback(
    async (action, successMessage, fallbackMessage) => {
      setIsMailboxActionRunning(true);
      setMailboxNotice("");
      setMailboxError("");
      try {
        await action();
        setMailboxNotice(successMessage);
        await loadMailboxes();
      } catch (requestError) {
        setMailboxError(requestError instanceof Error ? requestError.message : fallbackMessage);
      } finally {
        setIsMailboxActionRunning(false);
      }
    },
    [loadMailboxes]
  );

  const handleToggleMailboxEnabled = useCallback(
    async (row) => {
      await runMailboxAction(
        () =>
          apiRequest(`/mailboxes/${row.id}`, {
            method: "PATCH",
            body: {
              enabled: !row.enabled
            }
          }),
        row.enabled ? "Mailbox disabled" : "Mailbox enabled",
        "Failed to update mailbox"
      );
    },
    [runMailboxAction]
  );

  const handleTestMailbox = useCallback(
    async (row) => {
      await runMailboxAction(
        () =>
          apiRequest(`/mailboxes/${row.id}/test`, {
            method: "POST"
          }),
        `Mailbox test successful for ${row.name}`,
        "Mailbox test failed"
      );
    },
    [runMailboxAction]
  );

  const handleTriggerCollect = useCallback(
    async (row) => {
      await runMailboxAction(
        () =>
          apiRequest(`/mailboxes/${row.id}/trigger-collect`, {
            method: "POST"
          }),
        `Collection triggered for ${row.name}`,
        "Failed to trigger collection"
      );
    },
    [runMailboxAction]
  );

  const handleDeleteMailbox = useCallback(
    async (row) => {
      const confirmed = window.confirm(`Delete mailbox ${row.name}?`);
      if (!confirmed) {
        return;
      }

      await runMailboxAction(
        () =>
          apiRequest(`/mailboxes/${row.id}`, {
            method: "DELETE"
          }),
        "Mailbox deleted",
        "Failed to delete mailbox"
      );
    },
    [runMailboxAction]
  );

  const setProbeBusy = (probeId, isBusy) => {
    setProbeBusyById((previous) => {
      if (isBusy) {
        return {
          ...previous,
          [probeId]: true
        };
      }

      const next = { ...previous };
      delete next[probeId];
      return next;
    });
  };

  const runServiceProbe = useCallback(async (probeId) => {
    const probe = SERVICE_PROBES.find((item) => item.id === probeId);
    if (!probe) {
      return;
    }

    const checkedAt = new Date().toISOString();
    setProbeBusy(probeId, true);
    setServiceRows((previous) =>
      previous.map((row) =>
        row.id === probeId
          ? {
              ...row,
              status: "pending",
              metric: "Checking...",
              checkedAt: asDateTime(checkedAt),
              lastError: ""
            }
          : row
      )
    );

    try {
      const payload = await apiRequest(probe.endpoint);
      const metric = summarizeProbeMetric(probeId, payload);
      setServiceRows((previous) =>
        previous.map((row) =>
          row.id === probeId
            ? {
                ...row,
                status: "success",
                metric,
                checkedAt: asDateTime(new Date().toISOString()),
                lastError: ""
              }
            : row
        )
      );
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Probe failed";
      setServiceRows((previous) =>
        previous.map((row) =>
          row.id === probeId
            ? {
                ...row,
                status: "failed",
                metric: message,
                checkedAt: asDateTime(new Date().toISOString()),
                lastError: message
              }
            : row
        )
      );
    } finally {
      setProbeBusy(probeId, false);
    }
  }, []);

  const handleRunAllProbes = useCallback(async () => {
    setIsRunningAllProbes(true);
    await Promise.all(SERVICE_PROBES.map((probe) => runServiceProbe(probe.id)));
    setIsRunningAllProbes(false);
  }, [runServiceProbe]);

  const filteredServiceRows = useMemo(() => {
    if (serviceRoleFilter === "all") {
      return serviceRows;
    }
    return serviceRows.filter((row) => row.role === serviceRoleFilter);
  }, [serviceRoleFilter, serviceRows]);

  const mailboxColumns = useMemo(
    () => [
      { key: "name", label: "Mailbox Name" },
      { key: "server", label: "Server" },
      { key: "username", label: "Username" },
      { key: "mailbox", label: "Folder" },
      {
        key: "enabled",
        label: "Enabled",
        render: (row) => (
          <Chip
            size="small"
            variant="outlined"
            color={row.enabled ? "success" : "default"}
            label={row.enabled ? "Enabled" : "Disabled"}
          />
        )
      },
      { key: "updatedAt", label: "Updated" },
      {
        key: "actions",
        label: "Actions",
        render: (row) => (
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            <Button
              size="small"
              variant="outlined"
              disabled={isMailboxActionRunning}
              onClick={() => handleTestMailbox(row)}
            >
              Test
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={isMailboxActionRunning}
              onClick={() => handleTriggerCollect(row)}
            >
              Collect
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={isMailboxActionRunning}
              onClick={() => handleToggleMailboxEnabled(row)}
            >
              {row.enabled ? "Disable" : "Enable"}
            </Button>
            <Button
              size="small"
              color="error"
              variant="outlined"
              disabled={isMailboxActionRunning}
              onClick={() => handleDeleteMailbox(row)}
            >
              Delete
            </Button>
          </Stack>
        )
      }
    ],
    [
      handleDeleteMailbox,
      handleTestMailbox,
      handleToggleMailboxEnabled,
      handleTriggerCollect,
      isMailboxActionRunning
    ]
  );

  const serviceColumns = useMemo(
    () => [
      { key: "roleLabel", label: "User Type" },
      { key: "service", label: "Service" },
      { key: "purpose", label: "Purpose" },
      { key: "endpoint", label: "Endpoint" },
      { key: "metric", label: "Live Metric" },
      { key: "status", label: "Status" },
      { key: "checkedAt", label: "Last Check" },
      {
        key: "actions",
        label: "Actions",
        render: (row) => (
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            <Button
              size="small"
              variant="outlined"
              disabled={!!probeBusyById[row.id] || isRunningAllProbes}
              onClick={() => runServiceProbe(row.id)}
            >
              Probe
            </Button>
            {row.href ? (
              <Button size="small" variant="contained" component={Link} href={row.href}>
                Open
              </Button>
            ) : null}
          </Stack>
        )
      }
    ],
    [isRunningAllProbes, probeBusyById, runServiceProbe]
  );

  const mailboxSummary = useMemo(() => {
    const enabled = mailboxes.filter((row) => row.enabled).length;
    return `${enabled}/${mailboxes.length} mailboxes enabled`;
  }, [mailboxes]);

  const canCreateMailbox =
    mailboxForm.name.trim() &&
    mailboxForm.server.trim() &&
    mailboxForm.username.trim() &&
    mailboxForm.password;

  return (
    <AppLayout title="Settings">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard
            title="Mailbox Ingestion Workspace"
            subtitle="Real mailbox CRUD + connection and collection controls"
            action={
              <Chip
                label={`Operator: ${roleLabels[currentRole] || currentRole}`}
                size="small"
                color="primary"
                variant="outlined"
              />
            }
          >
            <Typography variant="body2" color="text.secondary">
              Server formats accepted: host, host:port, imap://host, or imaps://host.
            </Typography>
          </SectionCard>
        </Grid>

        <Grid item xs={12} md={5}>
          <SectionCard title="Add Mailbox" subtitle="Onboard IMAP source for collector">
            <Stack spacing={1.4}>
              <TextField
                size="small"
                label="Mailbox Name"
                value={mailboxForm.name}
                onChange={handleMailboxFormChange("name")}
              />
              <TextField
                size="small"
                label="Server"
                placeholder="imap.example.com:993"
                value={mailboxForm.server}
                onChange={handleMailboxFormChange("server")}
              />
              <TextField
                size="small"
                label="Username"
                value={mailboxForm.username}
                onChange={handleMailboxFormChange("username")}
              />
              <TextField
                size="small"
                label="Password"
                type="password"
                value={mailboxForm.password}
                onChange={handleMailboxFormChange("password")}
              />
              <TextField
                size="small"
                label="Folder"
                value={mailboxForm.mailbox}
                onChange={handleMailboxFormChange("mailbox")}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={mailboxForm.enabled}
                    onChange={handleMailboxFormChange("enabled")}
                  />
                }
                label="Enable mailbox right after creation"
              />
              <Box>
                <Button
                  variant="contained"
                  onClick={handleCreateMailbox}
                  disabled={!canCreateMailbox || isMailboxActionRunning}
                >
                  Create Mailbox
                </Button>
              </Box>
            </Stack>
          </SectionCard>
        </Grid>

        <Grid item xs={12} md={7}>
          <SectionCard
            title="Configured Mailboxes"
            subtitle={isLoadingMailboxes ? "Loading..." : mailboxSummary}
          >
            {isLoadingMailboxes ? (
              <Typography variant="body2" color="text.secondary">
                Loading mailboxes...
              </Typography>
            ) : mailboxes.length ? (
              <DataTable columns={mailboxColumns} rows={mailboxes} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No mailbox configured yet.
              </Typography>
            )}
          </SectionCard>
        </Grid>

        {mailboxNotice ? (
          <Grid item xs={12}>
            <Alert severity="success">{mailboxNotice}</Alert>
          </Grid>
        ) : null}

        {mailboxError ? (
          <Grid item xs={12}>
            <Alert severity="error">{mailboxError}</Alert>
          </Grid>
        ) : null}

        <Grid item xs={12}>
          <SectionCard
            title="Role-Based Service Console"
            subtitle="Helpful backend services for each user type"
            action={
              <Stack direction="row" spacing={1.2} alignItems="center">
                <TextField
                  select
                  size="small"
                  value={serviceRoleFilter}
                  onChange={(event) => setServiceRoleFilter(event.target.value)}
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="all">All roles</MenuItem>
                  {Object.keys(roleLabels).map((roleKey) => (
                    <MenuItem key={roleKey} value={roleKey}>
                      {roleLabels[roleKey]}
                    </MenuItem>
                  ))}
                </TextField>
                <Button
                  size="small"
                  variant="contained"
                  disabled={isRunningAllProbes}
                  onClick={handleRunAllProbes}
                >
                  {isRunningAllProbes ? "Probing..." : "Probe All"}
                </Button>
              </Stack>
            }
          >
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Probe calls are live and tenant-scoped. Failed probes usually mean auth/RBAC restrictions
              or missing data for that service.
            </Typography>
            <DataTable columns={serviceColumns} rows={filteredServiceRows} />
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

