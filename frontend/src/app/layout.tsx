import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MatDAO — Scientific Paper Due Diligence',
  description: 'Automated 9-dimension scoring for scientific research investment evaluation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
