// Worker giriş noktası. Cloudflare çalışma ortamı ana modülün her adlı dışa aktarımını bir giriş noktası sayar
// (sabitler "function or ExportedHandler değil" hatasıyla Worker'ı başlatmaz). Bu yüzden ana modül yalnız
// varsayılan işleyiciyi dışa aktarır; yardımcıların adlı dışa aktarımları testler için index.js'te kalır.
import worker from './index.js';

export default worker;
