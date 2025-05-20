const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  // disable: process.env.NODE_ENV === 'development' // Optional: disable PWA in dev
});

module.exports = withPWA({
  // your other next.js config options
  reactStrictMode: true,
});