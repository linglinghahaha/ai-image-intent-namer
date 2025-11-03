import { build } from "electron-builder";
import path from "node:path";

async function run(): Promise<void> {
  await build({
    config: {
      appId: "com.ai.image.intent.desktop",
      productName: "AI Image Intent Namer",
      directories: {
        app: path.resolve(__dirname, ".."),
        output: path.resolve(__dirname, "../dist-electron"),
        buildResources: path.resolve(__dirname, "../build"),
      },
      files: [
        "dist/**/*",
        "electron/main.js",
        "package.json",
      ],
      mac: {
        target: ["dmg"],
        category: "public.app-category.productivity",
      },
      win: {
        target: ["nsis"],
      },
      linux: {
        target: ["AppImage"],
        category: "Utility",
      },
    },
  });
}

run().catch((error) => {
  console.error("Electron build failed:", error);
  process.exit(1);
});
