import { Platform } from 'react-native';
import * as Crypto from 'expo-crypto';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import type { RequestOptions } from './api';
import type { DirectUpload, DocumentUpload, DocumentVersion } from './types';

export type MobileApi = <T>(path: string, body?: object, options?: RequestOptions) => Promise<T>;
export type PickedFile = { name: string; uri: string; file?: globalThis.File; size?: number };

export async function pickDocument(camera = false): Promise<PickedFile | null> {
  if (camera) {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) throw new Error('Permita o acesso à câmera nas configurações ou selecione um arquivo.');
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: .85, exif: false });
    if (result.canceled) return null;
    const asset = result.assets[0];
    return { uri: asset.uri, name: asset.fileName || 'foto.jpg', size: asset.fileSize, file: asset.file };
  }
  const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/jpeg', 'image/png'], copyToCacheDirectory: true, multiple: false });
  return result.canceled ? null : result.assets[0];
}

export async function uploadDocument(api: MobileApi, caseId: string, asset: PickedFile, previous?: DocumentVersion) {
  const extension = asset.name.split('.').pop()?.toLowerCase();
  const mime = extension === 'pdf' ? 'application/pdf' : extension === 'png' ? 'image/png' : ['jpg', 'jpeg'].includes(extension || '') ? 'image/jpeg' : '';
  if (!mime) throw new Error('Escolha um arquivo PDF, JPEG ou PNG.');
  const native = Platform.OS !== 'web' ? new File(asset.uri) : null;
  const size = asset.file?.size ?? asset.size ?? native?.size ?? 0;
  if (!size || size > 20 * 1024 * 1024) throw new Error('Escolha um arquivo com conteúdo e até 20 MiB.');
  try {
    const buffer = asset.file ? await asset.file.arrayBuffer() : native ? await native.arrayBuffer() : await (await fetch(asset.uri)).arrayBuffer();
    if (buffer.byteLength !== size) throw new Error('O arquivo mudou. Selecione-o novamente.');
    const hash = await Crypto.digest(Crypto.CryptoDigestAlgorithm.SHA256, buffer);
    const checksum = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
    const upload = await api<DocumentUpload>(previous ? `documents/${previous.documentId}/versions` : `cases/${caseId}/documents/uploads`,
      { filename: asset.name, sizeBytes: size, mime, ...(previous ? { previousVersion: previous.number } : {}) });
    if (upload.directUpload) {
      const authorization = await api<DirectUpload>(`uploads/${upload.uploadId}/authorize`, { checksum });
      const target = new URL(authorization.url);
      if (target.protocol !== 'https:' || target.username || target.password || authorization.method !== 'PUT') throw new Error('Destino de envio inválido.');
      const response = await fetch(target.href, { method: 'PUT', headers: authorization.headers, credentials: 'omit', redirect: 'error', body: buffer, signal: AbortSignal.timeout(60000) });
      if (!response.ok) throw new Error('Falha ao enviar o arquivo. Atualize a lista e envie uma nova versão.');
    } else await api(`uploads/${upload.uploadId}/content`, buffer, { binary: true });
    return await api<DocumentVersion>(`uploads/${upload.uploadId}/complete`, { checksum });
  } finally {
    // Only delete the temporary copy made by our picker, never an original file.
    if (native && asset.uri.startsWith(Paths.cache.uri) && native.exists) native.delete();
  }
}

export async function downloadDocument(api: MobileApi, item: DocumentVersion) {
  const bytes = await api<ArrayBuffer>(`documents/${item.documentId}/versions/${item.id}/content`, undefined, { download: true });
  const filename = item.filename.replace(/[\\/\x00-\x1f]/g, '_');
  if (Platform.OS === 'web') {
    const url = URL.createObjectURL(new Blob([bytes]));
    const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    return;
  }
  if (!await Sharing.isAvailableAsync()) throw new Error('Não foi possível abrir o compartilhamento neste aparelho.');
  const file = new File(Paths.cache, `${Crypto.randomUUID()}-${filename}`);
  try {
    file.create(); file.write(new Uint8Array(bytes));
    await Sharing.shareAsync(file.uri, { dialogTitle: 'Salvar ou abrir documento' });
  } finally { if (file.exists) file.delete(); }
}
