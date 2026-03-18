import { useRouter } from "next/router";
import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Grid,
  Stack,
  Typography
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import LoginIcon from "@mui/icons-material/Login";
import { getDefaultRouteForRole, roleLabels } from "access/roles";

const roles = [
  {
    id: "nextstep_admin",
    description: "Full platform access, tenant governance, and security controls.",
    access: "All modules: governance, integrations, settings, analytics"
  },
  {
    id: "client_admin",
    description: "Manage domains, policies, integrations, and onboarding.",
    access: "Domain lifecycle, integrations, compliance operations"
  },
  {
    id: "analyst_soc",
    description: "Monitor alerts, investigate anomalies, and respond.",
    access: "Operational dashboard, alerts, scoring, recommendations"
  },
  {
    id: "client_user",
    description: "Read dashboards, compliance, and risk summaries.",
    access: "Read-only reporting and posture visibility"
  }
];

export default function Login() {
  const router = useRouter();

  const handleLogin = (roleId) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("nextdmarc_role", roleId);
      router.push(getDefaultRouteForRole(roleId));
    }
  };

  return (
    <Box
      sx={{
        position: "relative",
        overflow: "hidden",
        minHeight: "100vh",
        backgroundImage:
          "linear-gradient(112deg, rgba(10,47,98,0.95) 0%, rgba(17,93,171,0.84) 54%, rgba(4,183,241,0.56) 100%)",
        py: { xs: 5, md: 9 },
        px: 2
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: -120,
          right: -120,
          width: 360,
          height: 360,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(92,214,255,0.42) 0%, rgba(92,214,255,0) 70%)"
        }}
      />
      <Container maxWidth="lg">
        <Box
          sx={{
            position: "relative",
            backgroundColor: alpha("#ffffff", 0.92),
            backdropFilter: "blur(8px)",
            borderRadius: 5,
            border: "1px solid rgba(255,255,255,0.55)",
            boxShadow: "0 20px 45px rgba(7, 31, 61, 0.28)",
            overflow: "hidden"
          }}
        >
          <Grid container>
            <Grid item xs={12} md={5}>
              <Box
                sx={{
                  height: "100%",
                  p: { xs: 3, md: 4 },
                  color: "white",
                  background:
                    "radial-gradient(95% 140% at 0% 0%, #2084ed 0%, #0f4c97 55%, #082a57 100%)"
                }}
              >
                <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 4 }}>
                  <Avatar
                    variant="rounded"
                    sx={{
                      bgcolor: "white",
                      color: "primary.main",
                      fontWeight: 800,
                      width: 44,
                      height: 44
                    }}
                  >
                    NS
                  </Avatar>
                  <Box>
                    <Typography sx={{ lineHeight: 1.1, fontWeight: 800 }}>NextStep</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.92 }}>
                      NextDmarc Platform
                    </Typography>
                  </Box>
                </Stack>

                <Typography variant="h4" sx={{ mb: 1.5 }}>
                  Secure your email domain posture
                </Typography>
                <Typography sx={{ opacity: 0.92, maxWidth: 360 }}>
                  Simulate each role and explore how NextDmarc supports collection,
                  detection, scoring, governance, and SOC workflows.
                </Typography>

                <Stack spacing={1.5} sx={{ mt: 4 }}>
                  <Stack direction="row" spacing={1.2} alignItems="center">
                    <ShieldOutlinedIcon fontSize="small" sx={{ color: "secondary.light" }} />
                    <Typography variant="body2">DMARC, SPF, DKIM insight at scale</Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.2} alignItems="center">
                    <ShieldOutlinedIcon fontSize="small" sx={{ color: "secondary.light" }} />
                    <Typography variant="body2">Multi-tenant role-based governance model</Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.2} alignItems="center">
                    <ShieldOutlinedIcon fontSize="small" sx={{ color: "secondary.light" }} />
                    <Typography variant="body2">SOC-ready alerting and response visibility</Typography>
                  </Stack>
                </Stack>
              </Box>
            </Grid>

            <Grid item xs={12} md={7}>
              <Box sx={{ p: { xs: 3, md: 4 } }}>
                <Typography variant="h5" sx={{ color: "primary.dark", mb: 0.5 }}>
                  Login with mock accounts
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Select one account to load permissions and navigation for that role.
                </Typography>

                <Grid container spacing={2}>
                  {roles.map((role) => (
                    <Grid item xs={12} sm={6} key={role.id}>
                      <Card
                        elevation={0}
                        sx={{
                          height: "100%",
                          border: "1px solid",
                          borderColor: "divider",
                          transition: "transform 0.2s ease, box-shadow 0.2s ease",
                          "&:hover": {
                            transform: "translateY(-2px)",
                            boxShadow: "0 12px 24px rgba(10, 47, 98, 0.12)"
                          }
                        }}
                      >
                        <CardContent sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
                          <Typography variant="subtitle1" sx={{ mb: 0.5 }}>
                            {roleLabels[role.id]}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                            {role.description}
                          </Typography>
                          <Divider sx={{ mb: 1.5 }} />
                          <Typography variant="caption" color="text.secondary" sx={{ mb: 2 }}>
                            Access scope: {role.access}
                          </Typography>
                          <Box sx={{ mt: "auto" }}>
                            <Button
                              fullWidth
                              variant="contained"
                              endIcon={<LoginIcon />}
                              onClick={() => handleLogin(role.id)}
                            >
                              Enter as {roleLabels[role.id]}
                            </Button>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </Container>
    </Box>
  );
}

