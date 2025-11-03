import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    root: process.cwd(),
    base: "./",
    resolve: {
      alias: {
        "@figma": path.resolve(__dirname, "src/figma"),
        "@desktop": path.resolve(__dirname, "src"),
      },
    },
    server: {
      port: Number(env.VITE_PORT || 5173),
      strictPort: true,
      fs: {
        // Allow Vite dev server to read the Figma export folder
        allow: [
          path.resolve(__dirname, "src"),
          path.resolve(__dirname, "../../.vscode/figma"),
        ],
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
      emptyOutDir: true,
    },
  };
});
