import { Box, Card, CardContent, Typography } from "@mui/material";

export default function SectionCard({ title, subtitle, children, action }) {
  return (
    <Card
      elevation={0}
      sx={{
        position: "relative",
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        "&::before": {
          content: '""',
          position: "absolute",
          inset: "0 0 auto 0",
          height: 4,
          background: "linear-gradient(90deg, #0f4c97 0%, #02b7f1 100%)"
        }
      }}
    >
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1.5 }}>
          <Box>
            <Typography variant="subtitle1" sx={{ color: "primary.dark" }}>
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary" sx={{ letterSpacing: "0.01em" }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          {action}
        </Box>
        <Box sx={{ mt: 2.2 }}>{children}</Box>
      </CardContent>
    </Card>
  );
}

