export const stats = [
  {
    label: "DMARC Compliance",
    value: "92%",
    helper: "+4% in 30 days"
  },
  {
    label: "Spoofing Attempts",
    value: "27",
    helper: "8 critical"
  },
  {
    label: "Unaligned Sources",
    value: "14",
    helper: "Review SPF/DKIM"
  },
  {
    label: "Threat Score",
    value: "Medium",
    helper: "Top risk: APAC"
  }
];

export const domains = [
  {
    id: "nx-001",
    name: "nextstep.tn",
    policy: "quarantine",
    compliance: "95%",
    risk: "Low"
  },
  {
    id: "nx-002",
    name: "nextdmarc.app",
    policy: "reject",
    compliance: "98%",
    risk: "Low"
  },
  {
    id: "nx-003",
    name: "partner-mail.tn",
    policy: "none",
    compliance: "76%",
    risk: "Medium"
  }
];

export const recentAlerts = [
  {
    id: "alert-1",
    title: "High volume spoofing",
    severity: "Critical",
    color: "error",
    detail: "215 failed DMARC from ASN 64512 (US)"
  },
  {
    id: "alert-2",
    title: "Policy misalignment",
    severity: "Warning",
    color: "warning",
    detail: "DKIM selector missing for marketing domain"
  },
  {
    id: "alert-3",
    title: "New sending source",
    severity: "Info",
    color: "info",
    detail: "Mailjet detected for nextstep.tn"
  }
];

export const reportPipeline = [
  {
    id: "rp-1",
    stage: "Collect",
    detail: "IMAP + API connectors",
    status: "Healthy"
  },
  {
    id: "rp-2",
    stage: "Parse",
    detail: "XML normalized",
    status: "Healthy"
  },
  {
    id: "rp-3",
    stage: "Analyze",
    detail: "SPF/DKIM/DMARC",
    status: "Healthy"
  },
  {
    id: "rp-4",
    stage: "Detect",
    detail: "Spoofing patterns",
    status: "Alerting"
  }
];

export const integrationItems = [
  {
    id: "int-1",
    name: "Microsoft Sentinel",
    status: "Connected",
    owner: "SOC"
  },
  {
    id: "int-2",
    name: "Splunk",
    status: "Pending",
    owner: "SOC"
  },
  {
    id: "int-3",
    name: "Slack",
    status: "Connected",
    owner: "Ops"
  }
];

export const recommendations = [
  {
    id: "rec-1",
    title: "Move partner-mail.tn to quarantine",
    impact: "Reduce spoofing by 30%",
    status: "In progress"
  },
  {
    id: "rec-2",
    title: "Fix SPF include chain",
    impact: "Align 12 sources",
    status: "Planned"
  },
  {
    id: "rec-3",
    title: "Rotate DKIM selector",
    impact: "Improve crypto hygiene",
    status: "Suggested"
  }
];

