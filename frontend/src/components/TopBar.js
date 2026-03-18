import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Toolbar,
  Typography
} from "@mui/material";
import { useLanguage } from "i18n/LanguageContext";

export default function TopBar({ title, roleLabel, onLogout }) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <AppBar position="sticky" color="inherit" elevation={0}>
      <Toolbar
        sx={{
          px: { xs: 2.5, md: 4 },
          py: 1.2,
          borderBottom: "1px solid",
          borderColor: "divider",
          gap: 2,
          background:
            "linear-gradient(112deg, rgba(255,255,255,0.9) 0%, rgba(247,251,255,0.93) 58%, rgba(236,247,255,0.8) 100%)"
        }}
      >
        <Avatar
          variant="rounded"
          sx={{
            width: 38,
            height: 38,
            bgcolor: "primary.dark",
            fontWeight: 800,
            fontSize: 14,
            boxShadow: "0 8px 18px rgba(10, 47, 98, 0.24)"
          }}
        >
          NS
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ lineHeight: 1.1, fontWeight: 700 }}>
            {t("topBar.platform", "NextDmarc Platform")}
          </Typography>
          <Typography variant="h6" sx={{ color: "primary.dark" }}>
            {title}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <FormControl
            size="small"
            sx={{
              minWidth: 132,
              "& .MuiOutlinedInput-root": {
                borderRadius: 2,
                backgroundColor: "#ffffff"
              }
            }}
          >
            <InputLabel id="language-select-label">{t("topBar.language", "Language")}</InputLabel>
            <Select
              labelId="language-select-label"
              value={language}
              label={t("topBar.language", "Language")}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="fr">Francais</MenuItem>
            </Select>
          </FormControl>
          <Chip
            label={`${t("topBar.role", "Role")}: ${roleLabel}`}
            color="primary"
            sx={{
              fontWeight: 700,
              bgcolor: "rgba(17,93,171,0.08)",
              border: "1px solid rgba(17,93,171,0.2)",
              color: "primary.dark"
            }}
          />
          <Button variant="outlined" color="primary" onClick={onLogout}>
            {t("topBar.logout", "Logout")}
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
