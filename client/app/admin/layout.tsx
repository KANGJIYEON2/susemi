import { ReactNode } from "react";
import AdminGate from "@/app/components/AdminGate";

export const metadata = {
  title: "수세미 admin",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AdminGate>{children}</AdminGate>;
}
