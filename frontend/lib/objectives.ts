export type ObjectiveId =
  | "calculate"
  | "compare"
  | "lookup"
  | "clean"
  | "summarize"
  | "pivot"
  | "chart"
  | "dashboard"
  | "analyze"
  | "find"
  | "report"
  | "ask"
  | "templates"
  | "growth"
  | "conditional"
  | "math"
  | "upload"
  | "home";

export type ActionTile = {
  id: ObjectiveId;
  label: string;
  desc: string;
  color: string; // icon bg
  icon: string; // lucide name key
};

export const HOME_ACTIONS: ActionTile[] = [
  {
    id: "calculate",
    label: "Calculate",
    desc: "Perform calculations (Sum, Avg, %, Count, Growth, etc.)",
    color: "bg-emerald-500",
    icon: "calculator",
  },
  {
    id: "compare",
    label: "Compare",
    desc: "Compare data between periods, categories, regions, etc.",
    color: "bg-blue-500",
    icon: "scale",
  },
  {
    id: "lookup",
    label: "Lookup / Match",
    desc: "VLOOKUP, XLOOKUP, Index Match & more powerful lookups",
    color: "bg-violet-500",
    icon: "search",
  },
  {
    id: "clean",
    label: "Clean Data",
    desc: "Remove duplicates, blanks, errors & clean your data",
    color: "bg-teal-500",
    icon: "broom",
  },
  {
    id: "summarize",
    label: "Summarize",
    desc: "Group data and get summary by category, region, date, etc.",
    color: "bg-orange-500",
    icon: "clipboard",
  },
  {
    id: "pivot",
    label: "Pivot Table",
    desc: "Create dynamic pivot tables in one click",
    color: "bg-green-500",
    icon: "table",
  },
  {
    id: "chart",
    label: "Charts",
    desc: "Create beautiful charts and visual insights",
    color: "bg-pink-500",
    icon: "chart",
  },
  {
    id: "dashboard",
    label: "Dashboard",
    desc: "Build interactive dashboards with KPI, charts & slicers",
    color: "bg-teal-600",
    icon: "monitor",
  },
  {
    id: "report",
    label: "Reports",
    desc: "Generate professional reports with key insights",
    color: "bg-indigo-500",
    icon: "file",
  },
  {
    id: "analyze",
    label: "Analyze (AI)",
    desc: "Let AI analyze your data and provide smart insights",
    color: "bg-blue-600",
    icon: "sparkles",
  },
];

export const SIDEBAR_ANALYZE: { id: ObjectiveId; label: string }[] = [
  { id: "calculate", label: "Calculate" },
  { id: "compare", label: "Compare" },
  { id: "lookup", label: "Lookup / Match" },
  { id: "clean", label: "Clean Data" },
  { id: "summarize", label: "Summarize" },
  { id: "pivot", label: "Pivot Table" },
  { id: "chart", label: "Charts" },
  { id: "dashboard", label: "Dashboard" },
  { id: "report", label: "Reports" },
];

export const SIDEBAR_SOLUTIONS = [
  { id: "sales_dashboard", label: "Sales Analysis", domain: "sales" },
  { id: "stock_dashboard", label: "Inventory Analysis", domain: "inventory" },
  { id: "pnl_summary", label: "Finance Analysis", domain: "finance" },
  { id: "employee_performance", label: "HR Analysis", domain: "hr" },
  { id: "order_analysis", label: "Marketing Analysis", domain: "ecommerce" },
  { id: "lead_analysis", label: "CRM Analysis", domain: "crm" },
] as const;

export const SUGGESTED_QUESTIONS = [
  "Top 10 customers by sales",
  "Monthly revenue trend",
  "Compare Dubai vs Abu Dhabi",
  "Find duplicate records",
];
