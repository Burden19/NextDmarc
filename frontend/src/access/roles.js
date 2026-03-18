export const roleLabels = {
  nextstep_admin: "NEXTSTEP Admin",
  client_admin: "Client Admin",
  analyst_soc: "Analyst SOC",
  client_user: "Client User"
};

export const navItems = [
  { href: "/", label: "Overview", roles: ["nextstep_admin", "client_admin", "analyst_soc", "client_user"] },
  { href: "/dashboard", label: "Dashboard", roles: ["nextstep_admin", "client_admin", "analyst_soc", "client_user"] },
  { href: "/domains", label: "Domains", roles: ["nextstep_admin", "client_admin"] },
  { href: "/reports", label: "Reports", roles: ["nextstep_admin", "client_admin", "analyst_soc", "client_user"] },
  { href: "/alerts", label: "Alerts", roles: ["nextstep_admin", "client_admin", "analyst_soc"] },
  { href: "/scoring", label: "Scoring", roles: ["nextstep_admin", "client_admin", "analyst_soc"] },
  { href: "/recommendations", label: "Recommendations", roles: ["nextstep_admin", "client_admin", "analyst_soc", "client_user"] },
  { href: "/integrations", label: "Integrations", roles: ["nextstep_admin", "client_admin"] },
  { href: "/governance", label: "Governance", roles: ["nextstep_admin", "client_admin"] },
  { href: "/settings", label: "Settings", roles: ["nextstep_admin", "client_admin"] }
];

export const routeAccess = navItems.reduce((acc, item) => {
  acc[item.href] = item.roles;
  return acc;
}, {});

export function isRouteAllowed(role, route) {
  const allowedRoles = routeAccess[route];
  if (!allowedRoles) {
    return true;
  }
  return allowedRoles.includes(role);
}

export function getDefaultRouteForRole(role) {
  const firstAllowed = navItems.find((item) => item.roles.includes(role));
  return firstAllowed ? firstAllowed.href : "/login";
}

