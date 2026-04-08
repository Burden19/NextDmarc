import { useState } from "react";
import { useRouter } from "next/router";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import LoginIcon from "@mui/icons-material/Login";
import { getDefaultRouteForRole, roleLabels } from "access/roles";
import { loginWithPassword, registerTenantAdmin } from "lib/authSession";

export default function Login() {
  const router = useRouter();
  const [loginForm, setLoginForm] = useState({
    tenantId: "",
    email: "",
    password: ""
  });
  const [registerForm, setRegisterForm] = useState({
    tenantName: "",
    adminEmail: "",
    adminPassword: ""
  });
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [registerError, setRegisterError] = useState("");
  const [registerSuccess, setRegisterSuccess] = useState("");

  const handleLoginChange = (field) => (event) => {
    setLoginForm((previous) => ({
      ...previous,
      [field]: event.target.value
    }));
  };

  const handleRegisterChange = (field) => (event) => {
    setRegisterForm((previous) => ({
      ...previous,
      [field]: event.target.value
    }));
  };

  const handleLogin = async () => {
    setLoginError("");
    setIsLoggingIn(true);

    try {
      const session = await loginWithPassword({
        tenant_id: loginForm.tenantId.trim(),
        email: loginForm.email.trim().toLowerCase(),
        password: loginForm.password
      });

      router.push(getDefaultRouteForRole(session.role));
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleRegister = async () => {
    setRegisterError("");
    setRegisterSuccess("");
    setIsRegistering(true);

    try {
      const response = await registerTenantAdmin({
        tenant_name: registerForm.tenantName.trim(),
        admin_email: registerForm.adminEmail.trim().toLowerCase(),
        admin_password: registerForm.adminPassword
      });

      const tenantId = String(response?.tenant_id || "");
      const role = String(response?.role || "");

      setLoginForm((previous) => ({
        ...previous,
        tenantId,
        email: registerForm.adminEmail.trim().toLowerCase()
      }));

      setRegisterSuccess(
        `Tenant created successfully. Tenant ID: ${tenantId}. Role: ${roleLabels[role] || role}.`
      );
    } catch (error) {
      setRegisterError(error instanceof Error ? error.message : "Tenant registration failed");
    } finally {
      setIsRegistering(false);
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
                  Login to backend
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Use tenant credentials to open a real backend-backed session.
                </Typography>

                <Grid container spacing={2.2}>
                  <Grid item xs={12}>
                    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider" }}>
                      <CardContent sx={{ display: "grid", gap: 1.6 }}>
                        <Typography variant="subtitle1">Login</Typography>
                        {loginError ? <Alert severity="error">{loginError}</Alert> : null}
                        <TextField
                          label="Tenant ID"
                          value={loginForm.tenantId}
                          onChange={handleLoginChange("tenantId")}
                          size="small"
                          fullWidth
                        />
                        <TextField
                          label="Email"
                          value={loginForm.email}
                          onChange={handleLoginChange("email")}
                          size="small"
                          type="email"
                          fullWidth
                        />
                        <TextField
                          label="Password"
                          value={loginForm.password}
                          onChange={handleLoginChange("password")}
                          size="small"
                          type="password"
                          fullWidth
                        />
                        <Button
                          fullWidth
                          variant="contained"
                          endIcon={<LoginIcon />}
                          onClick={handleLogin}
                          disabled={isLoggingIn}
                        >
                          {isLoggingIn ? "Signing in..." : "Sign in"}
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12}>
                    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider" }}>
                      <CardContent sx={{ display: "grid", gap: 1.6 }}>
                        <Typography variant="subtitle1">Register Tenant Admin</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Use this once to create a tenant and seed the first admin account.
                        </Typography>
                        {registerError ? <Alert severity="error">{registerError}</Alert> : null}
                        {registerSuccess ? <Alert severity="success">{registerSuccess}</Alert> : null}
                        <TextField
                          label="Tenant Name"
                          value={registerForm.tenantName}
                          onChange={handleRegisterChange("tenantName")}
                          size="small"
                          fullWidth
                        />
                        <TextField
                          label="Admin Email"
                          value={registerForm.adminEmail}
                          onChange={handleRegisterChange("adminEmail")}
                          size="small"
                          type="email"
                          fullWidth
                        />
                        <TextField
                          label="Admin Password"
                          value={registerForm.adminPassword}
                          onChange={handleRegisterChange("adminPassword")}
                          size="small"
                          type="password"
                          fullWidth
                        />
                        <Button
                          fullWidth
                          variant="outlined"
                          onClick={handleRegister}
                          disabled={isRegistering}
                        >
                          {isRegistering ? "Creating tenant..." : "Create Tenant Admin"}
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </Container>
    </Box>
  );
}

