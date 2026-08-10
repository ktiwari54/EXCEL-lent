import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EXCEL-lent — Data Analyst Engine",
  description: "Upload your data. Tell us what you need. Get the analysis. Your data analyst, built into Excel.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
