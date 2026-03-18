import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#115dab",
      light: "#3f85d8",
      dark: "#0a2f62",
      contrastText: "#ffffff"
    },
    secondary: {
      main: "#02b7f1",
      light: "#5cd6ff",
      dark: "#0086b8"
    },
    success: {
      main: "#1f8f5f"
    },
    warning: {
      main: "#e48e17"
    },
    error: {
      main: "#d14646"
    },
    text: {
      primary: "#0f233d",
      secondary: "#516b88"
    },
    background: {
      default: "#eef4fb",
      paper: "#ffffff"
    },
    divider: "#d7e5f7"
  },
  shadows: [
    "none",
    "0 1px 2px rgba(12, 40, 76, 0.06)",
    "0 3px 10px rgba(13, 43, 82, 0.08)",
    "0 10px 26px rgba(11, 39, 74, 0.10)",
    ...Array(21).fill("0 10px 26px rgba(11, 39, 74, 0.10)")
  ],
  shape: {
    borderRadius: 16
  },
  typography: {
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    h4: {
      fontWeight: 800,
      letterSpacing: "-0.02em",
      lineHeight: 1.1
    },
    h5: {
      fontWeight: 700,
      letterSpacing: "-0.01em",
      lineHeight: 1.2
    },
    h6: {
      fontWeight: 700,
      letterSpacing: "-0.01em"
    },
    subtitle1: {
      fontWeight: 650
    },
    subtitle2: {
      fontWeight: 600,
      color: "#516b88"
    },
    button: {
      fontWeight: 700,
      letterSpacing: "0"
    }
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage:
            "radial-gradient(circle at 14% 8%, rgba(92, 152, 228, 0.16) 0, rgba(92, 152, 228, 0) 33%), radial-gradient(circle at 92% 90%, rgba(2, 183, 241, 0.12) 0, rgba(2, 183, 241, 0) 35%)"
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #d7e5f7",
          boxShadow: "0 10px 26px rgba(11, 39, 74, 0.08)",
          borderRadius: 16
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          textTransform: "none",
          fontWeight: 700
        },
        containedPrimary: {
          backgroundImage: "linear-gradient(120deg, #0f4c97 0%, #115dab 60%, #1b75d8 100%)",
          boxShadow: "0 8px 18px rgba(17, 93, 171, 0.25)"
        },
        outlinedPrimary: {
          borderColor: "#b8d2f0",
          backgroundColor: "#f7fbff"
        }
      }
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          borderRadius: 8
        }
      }
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 700,
          color: "#1f3e63",
          backgroundColor: "#f6faff"
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(255,255,255,0.82)",
          backdropFilter: "blur(10px)"
        }
      }
    }
  }
});

export default theme;

