import { Suspense } from "react";
import "./print.css";

export default function PrintLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={null}>{children}</Suspense>;
}
