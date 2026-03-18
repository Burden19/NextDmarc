import { Card, CardContent, Typography } from "@mui/material";

export default function StatCard({ label, value, helper }) {
  return (
    <Card
      elevation={0}
      sx={{
        position: "relative",
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        "&::after": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          width: 5,
          height: "100%",
          background: "linear-gradient(180deg, #0f4c97 0%, #02b7f1 100%)"
        }
      }}
    >
      <CardContent sx={{ pl: 2.5 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ letterSpacing: "0.01em" }}>
          {label}
        </Typography>
        <Typography variant="h5" sx={{ mt: 0.8, color: "primary.dark" }}>
          {value}
        </Typography>
        {helper && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "inline-block", mt: 0.6 }}>
            {helper}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

