import './globals.css';
import NavBar from './NavBar';

export const metadata = {
  title: 'Aviator Analytics Dashboard',
  description: 'Real-time pattern and tracking analytics for Aviator',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <NavBar />
        <main className="main">
          {children}
        </main>
      </body>
    </html>
  );
}
