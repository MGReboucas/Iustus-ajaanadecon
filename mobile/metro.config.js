const { getDefaultConfig } = require('expo/metro-config');
const path = require('node:path');
const config = getDefaultConfig(__dirname);
// Separate lockfiles: expose only dependency-free shared contracts to Metro.
config.watchFolders = [...config.watchFolders, path.resolve(__dirname, '../contracts')];
module.exports = config;
