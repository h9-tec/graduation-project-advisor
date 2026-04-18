import { Fraunces, DM_Sans, Lemonada, JetBrains_Mono } from "next/font/google";

export const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display-latin",
  axes: ["opsz"],
  weight: ["200", "400", "800"],
  display: "swap",
});

export const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body-latin",
  weight: ["400", "500", "700"],
  display: "swap",
});

export const lemonada = Lemonada({
  subsets: ["arabic", "latin"],
  variable: "--font-display-arabic",
  weight: ["300", "500", "700"],
  display: "swap",
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "600"],
  display: "swap",
});
