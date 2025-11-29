import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "수세미",
  description: "수세미가 연말정산 공제 항목을 같이 뜯어봐요",
  icons: {
    icon: "/susemi.png",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-[#FFFBEA] text-slate-800 antialiased selection:bg-[#FFD860] selection:text-slate-900">
        {children}
      </body>
    </html>
  );
}
