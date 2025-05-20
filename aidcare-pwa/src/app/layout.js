// src/app/layout.js
import './globals.css'; // Import global styles

export const metadata = {
  title: 'AidCare AI Assistant',
  description: 'AI Medical Assistant for Healthcare Providers',
  manifest: '/manifest.json', // Link to your manifest in the public folder
  themeColor: '#0070f3',      // Match theme_color in manifest
  icons: { // For PWA, manifest handles icons, but good for general SEO/browser tabs
    icon: '/favicon.ico', // or '/icons/icon-192x192.png'
    apple: '/icons/apple-touch-icon.png', // Create an apple-touch-icon
  }
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}