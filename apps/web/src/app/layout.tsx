import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Memory Atlas — Your notebook",
  description: "A place for your photos, your words, and your voice.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    {/* Shared paper filters: torn/deckled edges and a faint hand-drawn wobble for icons. */}
    <svg className="svg-defs" aria-hidden="true" focusable="false">
      <filter id="ma-deckle" x="-4%" y="-8%" width="108%" height="116%">
        <feTurbulence type="fractalNoise" baseFrequency=".045" numOctaves="4" seed="8" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G" />
      </filter>
      <filter id="ma-rough" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="2" seed="2" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="1.4" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
    {children}
  </body></html>;
}
