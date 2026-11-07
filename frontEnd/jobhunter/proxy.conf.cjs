const target = process.env.JOBHUNTER_API_TARGET || 'https://localhost:8443';
const url = new URL(target);
if (url.protocol !== 'https:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
  throw new Error('Development API proxy is restricted to HTTPS loopback targets.');
}
module.exports = {
  '/api/**': { target, secure: false, changeOrigin: false },
  '/health': { target, secure: false, changeOrigin: false },
};
