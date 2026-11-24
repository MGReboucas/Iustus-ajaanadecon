/* global __dirname */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const { expo } = require('../app.json');
const eas = require('../eas.json');
const failures = [];
for (const profile of ['preview', 'production']) {
  const value = eas.build[profile]?.env?.EXPO_PUBLIC_API_ORIGIN;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash || url.hostname.endsWith('.example')) throw new Error();
  } catch { failures.push(`${profile}: configure uma origem pública HTTPS válida.`); }
}
if (process.env.EAS_BUILD) {
  try {
    const url = new URL(process.env.EXPO_PUBLIC_API_ORIGIN);
    if (url.protocol !== 'https:' || url.origin + '/' !== url.href) throw new Error();
  } catch { failures.push('A build não recebeu EXPO_PUBLIC_API_ORIGIN válida.'); }
}
for (const file of [expo.icon, expo.android.adaptiveIcon.foregroundImage, '../contracts/api.ts', '../contracts/validation.ts', '../contracts/events.json']) {
  if (!fs.existsSync(path.resolve(root, file))) failures.push(`Arquivo necessário ausente: ${file}`);
}
if (!expo.ios.bundleIdentifier || !expo.android.package) failures.push('Identificadores Android/iOS ausentes.');
if (eas.build.production.android.buildType !== 'app-bundle') failures.push('Google Play exige a build Android em AAB.');
if (failures.length) { failures.forEach(message => console.error(message)); process.exitCode = 1; }
else console.log('Configuração de build válida: API HTTPS, assets, contratos, APK de teste e AAB de produção.');
