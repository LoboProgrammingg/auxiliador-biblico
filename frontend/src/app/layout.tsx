import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Gentium_Book_Plus, Noto_Serif_Hebrew } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const atkinson = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-atkinson" });
const gentium = Gentium_Book_Plus({
  subsets: ["latin", "greek", "greek-ext"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  variable: "--font-gentium",
});
const hebrew = Noto_Serif_Hebrew({ subsets: ["hebrew"], weight: ["400", "600"], variable: "--font-hebrew" });

export const metadata: Metadata = {
  title: "Auxiliador Bíblico",
  description: "Um companheiro de fé, estudo e oração, com a Bíblia completa e citações conferidas.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={`${atkinson.variable} ${gentium.variable} ${hebrew.variable}`}>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
