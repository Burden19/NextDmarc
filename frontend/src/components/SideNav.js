import Link from "next/link";
import { useRouter } from "next/router";
import {
  Box,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PublicIcon from "@mui/icons-material/Public";
import DescriptionIcon from "@mui/icons-material/Description";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import InsightsIcon from "@mui/icons-material/Insights";
import GavelIcon from "@mui/icons-material/Gavel";
import LanIcon from "@mui/icons-material/Lan";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import SettingsIcon from "@mui/icons-material/Settings";
import { navItems } from "access/roles";
import { useLanguage } from "i18n/LanguageContext";

const navItemsWithIcons = navItems.map((item) => {
  const iconMap = {
    "/": DashboardIcon,
    "/dashboard": InsightsIcon,
    "/domains": PublicIcon,
    "/reports": DescriptionIcon,
    "/alerts": WarningAmberIcon,
    "/scoring": InsightsIcon,
    "/recommendations": AutoFixHighIcon,
    "/integrations": LanIcon,
    "/governance": GavelIcon,
    "/settings": SettingsIcon
  };

  return {
    ...item,
    icon: iconMap[item.href]
  };
});

export default function SideNav({ drawerWidth, role }) {
  const router = useRouter();
  const { t } = useLanguage();
  const visibleItems = navItemsWithIcons.filter((item) => item.roles.includes(role));

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          borderRight: "1px solid",
          borderColor: "divider",
          background:
            "linear-gradient(180deg, rgba(250,253,255,0.96) 0%, rgba(246,250,255,0.93) 100%)"
        }
      }}
    >
      <Box
        sx={{
          px: 3,
          py: 3.5,
          color: "white",
          background: "linear-gradient(130deg, #082a57 0%, #0f4c97 60%, #1e78db 100%)",
          boxShadow: "inset 0 -1px 0 rgba(255,255,255,0.12)"
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 800 }}>
          NextDmarc
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.9 }}>
          {t("sideNav.analyzer", "DMARC Analyzer")}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            display: "inline-flex",
            mt: 1.5,
            px: 1,
            py: 0.3,
            borderRadius: 1,
            bgcolor: "rgba(255,255,255,0.16)",
            border: "1px solid rgba(255,255,255,0.22)"
          }}
        >
          NextStep SOC
        </Typography>
      </Box>
      <Divider />
      <List sx={{ px: 1, py: 1.2 }}>
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const selected = router.pathname === item.href;
          return (
            <Link href={item.href} key={item.href} passHref legacyBehavior>
              <ListItemButton
                selected={selected}
                sx={{
                  borderRadius: 2,
                  mx: 1,
                  my: 0.45,
                  border: "1px solid transparent",
                  transition: "all 0.2s ease",
                  "&:hover": {
                    backgroundColor: "#edf5ff",
                    borderColor: "#d2e2f7"
                  },
                  "&.Mui-selected": {
                    background: "linear-gradient(90deg, rgba(17,93,171,0.12) 0%, rgba(2,183,241,0.1) 100%)",
                    border: "1px solid #bfd7f5"
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <Icon color={selected ? "primary" : "action"} />
                </ListItemIcon>
                <ListItemText
                  primary={t(`pages.${item.href}`, item.label)}
                  primaryTypographyProps={{
                    fontWeight: selected ? 700 : 500,
                    color: selected ? "primary.dark" : "text.primary",
                    letterSpacing: "0.01em"
                  }}
                />
              </ListItemButton>
            </Link>
          );
        })}
      </List>
      <Box sx={{ px: 3, py: 3, mt: "auto", borderTop: "1px solid", borderColor: "divider" }}>
        <Typography variant="caption" color="text.secondary">
          {t("sideNav.environment", "Environment: SOC Ready")}
        </Typography>
      </Box>
    </Drawer>
  );
}
