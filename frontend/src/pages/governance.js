import { Grid, Typography } from "@mui/material";
import AppLayout from "components/AppLayout";
import SectionCard from "components/SectionCard";

const policies = [
  "Tenant isolation enforced",
  "Role-based access control",
  "Domain ownership validation",
  "Audit logs and compliance exports"
];

export default function Governance() {
  return (
    <AppLayout title="Governance">
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <SectionCard title="Multi-Tenant Controls" subtitle="Access + audit">
            {policies.map((policy) => (
              <Typography key={policy} variant="body2" sx={{ mb: 1 }}>
                {policy}
              </Typography>
            ))}
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <SectionCard title="User Privileges" subtitle="Four-actor roles">
            <Typography variant="body2" sx={{ mb: 1 }}>
              NEXTSTEP Admin oversees global configuration, tenants, and security.
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Client Admin manages domains, policies, and integrations.
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Analyst SOC investigates alerts and coordinates response.
            </Typography>
            <Typography variant="body2">
              Client User consumes dashboards, reports, and compliance status.
            </Typography>
          </SectionCard>
        </Grid>
      </Grid>
    </AppLayout>
  );
}

