import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import { Box, Button, Typography } from "@mui/material";
import TopBar from "components/TopBar";
import SideNav from "components/SideNav";
import { getDefaultRouteForRole, isRouteAllowed, roleLabels } from "access/roles";
import { useLanguage } from "i18n/LanguageContext";
import { getAuthSession, logoutAuthSession } from "lib/authSession";

const drawerWidth = 260;

export default function AppLayout({ title, children }) {
  const router = useRouter();
  const { t } = useLanguage();
  const [role, setRole] = useState(null);
  const [accessDenied, setAccessDenied] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const session = getAuthSession();
    if (!session || !session.role) {
      router.push("/login");
      return;
    }

    setRole(session.role);
  }, [router]);

  useEffect(() => {
    if (!role) {
      return;
    }

    if (!isRouteAllowed(role, router.pathname)) {
      setAccessDenied(true);
      router.push(getDefaultRouteForRole(role));
      return;
    }

    setAccessDenied(false);
  }, [role, router]);

  const roleLabel = useMemo(() => {
    return t(`roles.${role}`, roleLabels[role] ?? t("layout.unknownRole", "Unknown"));
  }, [role, t]);

  const localizedTitle = useMemo(() => {
    return t(`pages.${router.pathname}`, title);
  }, [router.pathname, t, title]);

  const handleLogout = async () => {
    await logoutAuthSession();
    setRole(null);
    router.push("/login");
  };

  if (!role) {
    return null;
  }

  return (
    <Box
      sx={{
        display: "flex",
        minHeight: "100vh",
        backgroundColor: "background.default",
        backgroundImage:
          "radial-gradient(circle at 82% 16%, rgba(63,133,216,0.14) 0%, rgba(63,133,216,0) 32%)"
      }}
    >
      <SideNav drawerWidth={drawerWidth} role={role} />
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <TopBar title={localizedTitle} roleLabel={roleLabel} onLogout={handleLogout} />
        <Box sx={{ flex: 1, px: { xs: 2.2, md: 4 }, py: { xs: 2, md: 3 } }}>
          {accessDenied ? (
            <Box
              sx={{
                maxWidth: 520,
                mx: "auto",
                textAlign: "center",
                mt: 8,
                p: 4,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                backgroundColor: "background.paper"
              }}
            >
              <Typography variant="h5" sx={{ mb: 1 }}>
                {t("layout.accessDeniedTitle", "Access denied")}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {t("layout.accessDeniedMessage", "Your role does not allow access to this page.")}
              </Typography>
              <Button variant="contained" onClick={() => router.push(getDefaultRouteForRole(role))}>
                {t("layout.goToAllowedPage", "Go to allowed page")}
              </Button>
            </Box>
          ) : (
            children
          )}
        </Box>
      </Box>
    </Box>
  );
}
