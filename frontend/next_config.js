module.exports = {
  trailingSlash: true,
  output: 'export',
  env: { NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000' },
};