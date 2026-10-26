/*
 * Runtime configuration for CampusHelp AI.
 *
 * Vite copies this file to dist/config.js, so it can be edited on the static
 * host after a build without rebuilding the app.
 *
 *   apiBaseUrl: the deployed backend origin, e.g. "https://campushelp-api.onrender.com".
 *               Leave empty to use VITE_API_BASE_URL from the build. Production
 *               builds leave that empty too, which means the same origin as the page.
 *   useMock:    true to answer from the local mock instead of the backend.
 */
window.CAMPUSHELP_CONFIG = window.CAMPUSHELP_CONFIG || {
  apiBaseUrl: '',
  useMock: null,
}
