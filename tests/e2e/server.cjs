// Processos próprios do teste, sem shell e sem reutilizar o backend de desenvolvimento.
const { spawn } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const backend = process.argv[2] === 'backend';
const python = process.env.IUSTUS_TEST_PYTHON || path.join(root, 'backend/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const child = spawn(backend ? python : process.execPath, backend ? [
  'manage.py', 'runserver', `127.0.0.1:${process.env.IUSTUS_TEST_API_PORT || '8000'}`, '--noreload', '--settings=config.settings.e2e',
] : ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', process.env.IUSTUS_TEST_WEB_PORT || '3000'], {
  cwd: path.join(root, backend ? 'backend' : 'frontend'), windowsHide: true, stdio: 'inherit',
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill());
child.on('exit', code => process.exit(code || 0));
child.on('error', error => { console.error(error.message); process.exit(1); });
