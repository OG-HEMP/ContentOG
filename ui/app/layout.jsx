import '@/styles/globals.css';
import AppShell from '@/components/AppShell';

export const metadata = {
  title: 'ContentOG UI',
  description: 'SEO intelligence graph interface'
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
