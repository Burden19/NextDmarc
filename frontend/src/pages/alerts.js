import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Grid,
  Stack,
  Typography
} from "@mui/material";
import AppLayout from "components/AppLayout";
import DataTable from "components/DataTable";
import SectionCard from "components/SectionCard";
import { apiRequest, toQueryString } from "lib/apiClient";
import { getApiBaseUrl, getAuthSession } from "lib/authSession";

function mapSeverityLabel(severity) {
  const normalized = String(severity || "").toLowerCase();
  if (!normalized) {
    return "UNKNOWN";
  }
  return normalized.toUpperCase();
}

function normalizeAlertRow(item) {
  return {
    id: item.id,
    message: item.message,
    severity: item.severity,
    status: item.status,
    assignee: item.assignee || "-",
    escalationLevel: item.escalation_level,
    updatedAt: new Date(item.updated_at).toLocaleString()
  };
}

function buildAlertsWebSocketUrl(tenantId) {
  const apiBaseUrl = getApiBaseUrl();
  const wsBaseUrl = apiBaseUrl.startsWith("https://")
    ? apiBaseUrl.replace("https://", "wss://")
    : apiBaseUrl.replace("http://", "ws://");
  return `${wsBaseUrl}/alerts/ws?tenant_id=${encodeURIComponent(tenantId)}`;
}

function upsertAlertRow(existingRows, incomingItem) {
  const mapped = normalizeAlertRow(incomingItem);
  const existingIndex = existingRows.findIndex((item) => item.id === mapped.id);
  if (existingIndex < 0) {
    return [mapped, ...existingRows];
  }

  const cloned = [...existingRows];
  cloned[existingIndex] = mapped;
  return cloned;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [realtimeState, setRealtimeState] = useState("disconnected");

  const role = useMemo(() => getAuthSession()?.role || "ui-user", []);

  const loadAlerts = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await apiRequest(`/alerts${toQueryString({ page: 1, page_size: 25 })}`);
      setAlerts((response?.items || []).map((item) => normalizeAlertRow(item)));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load alerts");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const applyTriageResponse = useCallback((response) => {
    const updated = response?.alert;
    if (!updated) {
      return;
    }
    setAlerts((previous) => upsertAlertRow(previous, updated));
  }, []);

  const runAlertAction = useCallback(
    async (actionCall, successMessage) => {
      setIsActing(true);
      setError("");
      setNotice("");
      try {
        const response = await actionCall();
        applyTriageResponse(response);
        setNotice(successMessage);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Alert action failed");
      } finally {
        setIsActing(false);
      }
    },
    [applyTriageResponse]
  );

  const handleStatusInvestigating = useCallback(
    async (alertId) => {
      await runAlertAction(
        () =>
          apiRequest(`/alerts/${alertId}/status`, {
            method: "POST",
            body: {
              status: "investigating",
              actor: role,
              comment: "Set to investigating from UI"
            }
          }),
        "Alert status updated"
      );
    },
    [role, runAlertAction]
  );

  const handleAssign = useCallback(
    async (alertId, currentAssignee) => {
      const suggested = currentAssignee && currentAssignee !== "-" ? currentAssignee : role;
      const assignee = window.prompt("Assign alert to", suggested);
      if (!assignee) {
        return;
      }

      await runAlertAction(
        () =>
          apiRequest(`/alerts/${alertId}/assign`, {
            method: "POST",
            body: {
              assignee,
              actor: role,
              comment: "Assignment updated from UI"
            }
          }),
        "Alert assignment updated"
      );
    },
    [role, runAlertAction]
  );

  const handleComment = useCallback(
    async (alertId) => {
      const comment = window.prompt("Add triage comment");
      if (!comment) {
        return;
      }

      await runAlertAction(
        () =>
          apiRequest(`/alerts/${alertId}/comment`, {
            method: "POST",
            body: {
              comment,
              actor: role
            }
          }),
        "Alert comment added"
      );
    },
    [role, runAlertAction]
  );

  const handleEscalate = useCallback(
    async (alertId) => {
      await runAlertAction(
        () =>
          apiRequest(`/alerts/${alertId}/escalate`, {
            method: "POST",
            body: {
              actor: role,
              comment: "Escalated from UI"
            }
          }),
        "Alert escalated"
      );
    },
    [role, runAlertAction]
  );

  const columns = useMemo(
    () => [
      { key: "message", label: "Message" },
      {
        key: "severity",
        label: "Severity",
        render: (row) => (
          <Chip
            label={mapSeverityLabel(row.severity)}
            size="small"
            color={
              row.severity === "critical" || row.severity === "high"
                ? "error"
                : row.severity === "medium"
                  ? "warning"
                  : "success"
            }
            variant="outlined"
          />
        )
      },
      { key: "status", label: "Status" },
      { key: "assignee", label: "Assignee" },
      { key: "escalationLevel", label: "Escalation" },
      { key: "updatedAt", label: "Updated" },
      {
        key: "actions",
        label: "Actions",
        render: (row) => (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              size="small"
              variant="outlined"
              disabled={isActing}
              onClick={() => handleStatusInvestigating(row.id)}
            >
              Investigate
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={isActing}
              onClick={() => handleAssign(row.id, row.assignee)}
            >
              Assign
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={isActing}
              onClick={() => handleComment(row.id)}
            >
              Comment
            </Button>
            <Button
              size="small"
              color="warning"
              variant="contained"
              disabled={isActing}
              onClick={() => handleEscalate(row.id)}
            >
              Escalate
            </Button>
          </Stack>
        )
      }
    ],
    [handleAssign, handleComment, handleEscalate, handleStatusInvestigating, isActing]
  );

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  useEffect(() => {
    const session = getAuthSession();
    if (!session?.tenantId) {
      return () => undefined;
    }

    let isStopped = false;
    let socket;
    let reconnectTimer;

    const connect = () => {
      setRealtimeState("connecting");
      socket = new WebSocket(buildAlertsWebSocketUrl(session.tenantId));

      socket.onopen = () => {
        setRealtimeState("connected");
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "alert.heartbeat") {
            return;
          }

          if (payload.payload?.alert) {
            setAlerts((previous) => upsertAlertRow(previous, payload.payload.alert));
            return;
          }

          if (payload.alert_id) {
            setAlerts((previous) =>
              upsertAlertRow(previous, {
                id: payload.alert_id,
                message: payload.payload?.message || `Realtime event: ${payload.type}`,
                severity: payload.payload?.severity || "medium",
                status: payload.payload?.status || "new",
                assignee: payload.payload?.assignee || null,
                escalation_level: payload.payload?.escalation_level || 0,
                updated_at: new Date().toISOString()
              })
            );
          }
        } catch {
          return;
        }
      };

      socket.onclose = () => {
        setRealtimeState("disconnected");
        if (!isStopped) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      socket.onerror = () => {
        setRealtimeState("disconnected");
      };
    };

    connect();
    return () => {
      isStopped = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (socket && socket.readyState <= 1) {
        socket.close();
      }
    };
  }, []);

  return (
    <AppLayout title="Alerts">
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <SectionCard title="Active Alerts" subtitle="Live DMARC anomalies">
            <Box sx={{ mb: 1.5 }}>
              <Chip
                label={`Realtime: ${realtimeState}`}
                color={realtimeState === "connected" ? "success" : "default"}
                variant="outlined"
                size="small"
              />
            </Box>
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading alerts...
              </Typography>
            ) : alerts.length ? (
              <DataTable columns={columns} rows={alerts} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No alerts available for this tenant yet.
              </Typography>
            )}
          </SectionCard>
        </Grid>
        <Grid item xs={12}>
          <SectionCard title="Response Guidance">
            <Typography variant="body2" color="text.secondary">
              Analysts validate spoofing, escalate via SOAR, and update
              suppression or allow-lists. Critical events trigger real-time
              notifications and IOC exports.
            </Typography>
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

