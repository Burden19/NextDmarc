import "styles/globals.css";
import { CssBaseline, ThemeProvider } from "@mui/material";
import theme from "theme";
import { LanguageProvider } from "i18n/LanguageContext";

export default function App({ Component, pageProps }) {
  return (
    <ThemeProvider theme={theme}>
      <LanguageProvider>
        <CssBaseline />
        <Component {...pageProps} />
      </LanguageProvider>
    </ThemeProvider>
  );
}

