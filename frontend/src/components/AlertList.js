import {
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  Typography
} from "@mui/material";
import { alpha } from "@mui/material/styles";

const severityStyles = {
  error: {
    bg: "#ffeef0",
    text: "#b4232c",
    border: "#f2b7bc"
  },
  warning: {
    bg: "#fff6e9",
    text: "#b56f00",
    border: "#f0cf97"
  },
  success: {
    bg: "#ebf8f1",
    text: "#1f7c53",
    border: "#a7dbc1"
  },
  info: {
    bg: "#edf5ff",
    text: "#16508f",
    border: "#bdd7f5"
  }
};

export default function AlertList({ items }) {
  return (
    <List sx={{ p: 0 }}>
      {items.map((alert) => {
        const style = severityStyles[alert.color] ?? severityStyles.info;

        return (
        <ListItem
          key={alert.id}
          sx={{
            px: 2,
            py: 1.35,
            borderRadius: 2.2,
            mb: 1.2,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            boxShadow: `0 2px 8px ${alpha("#0f3368", 0.05)}`
          }}
        >
          <ListItemText
            primary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.1 }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: style.text,
                    boxShadow: `0 0 0 5px ${alpha(style.text, 0.12)}`
                  }}
                />
                <Typography variant="subtitle2">{alert.title}</Typography>
                <Chip
                  label={alert.severity}
                  size="small"
                  sx={{
                    bgcolor: style.bg,
                    color: style.text,
                    border: `1px solid ${style.border}`
                  }}
                />
              </Box>
            }
            secondary={<Typography variant="body2" color="text.secondary">{alert.detail}</Typography>}
          />
        </ListItem>
        );
      })}
    </List>
  );
}

