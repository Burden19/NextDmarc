import {
  Chip,
  TableContainer,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper
} from "@mui/material";

export default function DataTable({ columns, rows }) {
  const renderCell = (value, key) => {
    if (key === "status" && typeof value === "string") {
      const normalized = value.toLowerCase();
      if (normalized.includes("ok") || normalized.includes("success") || normalized.includes("completed")) {
        return <Chip size="small" color="success" variant="outlined" label={value} />;
      }
      if (normalized.includes("warn") || normalized.includes("pending")) {
        return <Chip size="small" color="warning" variant="outlined" label={value} />;
      }
      if (normalized.includes("error") || normalized.includes("failed")) {
        return <Chip size="small" color="error" variant="outlined" label={value} />;
      }
      return <Chip size="small" color="primary" variant="outlined" label={value} />;
    }

    return value;
  };

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderColor: "divider", borderRadius: 3 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column.key}>{column.label}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow
              key={row.id ?? index}
              sx={{
                "&:nth-of-type(even)": { backgroundColor: "#fbfdff" },
                "&:last-child td": { borderBottom: 0 }
              }}
            >
              {columns.map((column) => (
                <TableCell key={column.key}>
                  {typeof column.render === "function"
                    ? column.render(row)
                    : renderCell(row[column.key], column.key)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

