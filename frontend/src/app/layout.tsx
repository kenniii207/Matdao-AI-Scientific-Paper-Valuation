/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from 'next';
import { Inter, Manrope } from 'next/font/google';
import './globals.css';

export const metadata: Metadata = {
  title: 'MatDAO — Scientific Paper Due Diligence',
  description: 'Automated 9-dimension scoring for scientific research investment evaluation',
};

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const manrope = Manrope({
  subsets: ['latin'],
  variable: '--font-manrope',
  display: 'swap',
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        />
      </head>
      <body className={`${inter.variable} ${manrope.variable} min-h-screen antialiased bg-surface-container-lowest text-on-surface`}>
        {children}
      </body>
    </html>
  );
}
